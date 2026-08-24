"""Owner-only persistent llama-server supervisor for CORE4 delegation."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

from .model_cache import ModelCache
from .servers import LlamaCppServerAdapter
from .service import AdapterService, AdapterError


class SupervisorError(RuntimeError):
    pass


def runtime_root() -> Path:
    override = os.environ.get("CORE4_SUPERVISOR_RUNTIME_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("XDG_RUNTIME_DIR")
    return ((Path(base) / "core4-local-worker") if base else
            (Path("/tmp") / f"core4-local-worker-{os.getuid()}"))


def state_root() -> Path:
    override = os.environ.get("CORE4_SUPERVISOR_STATE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    base = os.environ.get("XDG_STATE_HOME")
    return ((Path(base) / "core4-local-worker") if base else
            (Path.home() / ".local/state/core4-local-worker"))


def _private_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _http_json(url: str, timeout: float = 2.0) -> tuple[int, dict[str, Any]]:
    try:
        with urllib_request.urlopen(url, timeout=timeout) as response:
            return int(response.status), json.loads(response.read().decode("utf-8"))
    except (OSError, urllib_error.URLError, json.JSONDecodeError):
        return 0, {}


class Backend(Protocol):
    def status(self) -> dict[str, Any]: ...
    def warm(self) -> dict[str, Any]: ...
    def release(self, service_lease_id: str | None = None) -> dict[str, Any]: ...
    def preemption_status(self, service_lease_id: str | None = None) -> dict[str, Any]: ...
    def drain(self) -> dict[str, Any]: ...
    def evict(self) -> dict[str, Any]: ...
    def poll(self) -> None: ...
    def close(self) -> None: ...


@dataclass
class _ServiceSlot:
    slot_id: str
    handle: str
    endpoint_descriptor: dict[str, Any]
    owner_id: str
    cache_lease: Any
    gpu_uuids: tuple[str, ...]
    compatibility_key: str
    service_lease_id: str | None = None
    state: str = "idle"
    idle_since: float | None = None


class ProductionBackend:
    """Own a bounded, demand-driven pool of isolated llama model services."""

    def __init__(self, repo_root: str | Path, *, profile: dict[str, Any] | None = None,
                 cache: Any = None, runtime: Any = None, adapter: Any = None,
                 service: Any = None):
        self.repo_root = Path(repo_root).resolve()
        skill_root = Path(__file__).resolve().parents[1]
        self.profile = profile or tomllib.loads(
            (skill_root / "config/production-profile.toml").read_text(encoding="utf-8")
        )
        storage = self.profile["storage"]
        self.cache = cache or ModelCache(storage["cache_root"], storage["canonical_root"])
        todo_root = Path(__file__).resolve().parents[2] / "todo-orchestrator"
        if str(todo_root) not in sys.path:
            sys.path.insert(0, str(todo_root))
        from todo_orchestrator.runtime import RuntimeFacade
        self.runtime = runtime or RuntimeFacade(self.repo_root)
        self.adapter = adapter or LlamaCppServerAdapter(str(self.profile["server"]["binary"]))
        self.service = service or AdapterService()
        if service is None:
            self.service.register("llama", self.adapter)
        policy = self.profile.get("deployment_policy", {})
        configured = int(policy.get("max_real_workers", 1))
        validation_override = os.environ.get("CORE4_VALIDATION_MAX_REAL_WORKERS")
        self.max_slots = min(2, max(1, int(validation_override or configured)))
        self._slots: dict[str, _ServiceSlot] = {}
        self._leases: dict[str, str] = {}
        self._preempted_leases: set[str] = set()
        self._start_lock = threading.Lock()
        self.draining = False
        self.ttl = float(policy.get("hot_idle_seconds", 900))

    def _candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate = next((item for item in self.profile.get("candidates", []) if item.get("id") == candidate_id), None)
        if not isinstance(candidate, dict):
            raise SupervisorError(f"active model is absent from production profile: {candidate_id}")
        return candidate

    def _version(self, binary: str) -> str:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30, check=False)
        return (result.stdout + result.stderr)[-8000:]

    def _free_port(self, base: int) -> int:
        for port in range(base, min(base + 32, 65536)):
            probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
                probe.bind(("127.0.0.1", port))
                return port
            except OSError:
                pass
            finally:
                probe.close()
        raise SupervisorError("no free loopback port is available in the configured range")

    def _healthy(self, slot: _ServiceSlot) -> bool:
        health = self.service.health("llama", slot.handle)
        if not health.get("healthy"):
            return False
        base = str(slot.endpoint_descriptor["base_url"]).removesuffix("/v1")
        status, models = _http_json(base + "/v1/models")
        return status == 200 and bool(models.get("data"))

    def _compatibility(self, values: dict[str, Any]) -> str:
        payload = json.dumps(values, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def status(self) -> dict[str, Any]:
        summaries = []
        for slot in sorted(self._slots.values(), key=lambda item: item.slot_id):
            summaries.append({
                **slot.endpoint_descriptor, "slot_id": slot.slot_id,
                "state": slot.state, "leased": slot.service_lease_id is not None,
                "healthy": self._healthy(slot),
            })
        active = len(self._leases)
        endpoint = summaries[0] if len(summaries) == 1 else None
        return {
            "format": "CORE4-MODEL-SUPERVISOR/1", "running": bool(summaries),
            "healthy": bool(summaries) and all(item["healthy"] for item in summaries),
            "draining": self.draining, "clients": active, "active_leases": active,
            "capacity": self.max_slots, "idle_ttl_seconds": self.ttl,
            "endpoint": endpoint, "slots": summaries,
        }

    def _lease(self, slot: _ServiceSlot, *, reused: bool) -> dict[str, Any]:
        if slot.service_lease_id is not None:
            raise SupervisorError("model service slot already has an active lease")
        lease_id = str(uuid.uuid4())
        if not self.runtime.host.set_priority(slot.owner_id, "active_local_delegation"):
            self._evict_slot(slot.slot_id)
            raise SupervisorError("model service lost its host reservation")
        slot.service_lease_id = lease_id
        slot.state = "active"
        slot.idle_since = None
        self._leases[lease_id] = slot.slot_id
        return {
            **slot.endpoint_descriptor, "slot_id": slot.slot_id,
            "service_lease_id": lease_id, "reused": reused,
        }

    def warm(self) -> dict[str, Any]:
        if self.draining:
            raise SupervisorError("model service is draining for foreground preemption")
        for slot in sorted(self._slots.values(), key=lambda item: item.slot_id):
            if slot.service_lease_id is None and self._healthy(slot):
                return self._lease(slot, reused=True)
        for slot in list(self._slots.values()):
            if slot.service_lease_id is None and not self._healthy(slot):
                self._evict_slot(slot.slot_id)
        if len(self._slots) >= self.max_slots:
            raise SupervisorError("resource_unavailable: all model service slots are leased; retryable=true")
        with self._start_lock:
            # A prior request may have populated an idle slot while this caller waited.
            for slot in sorted(self._slots.values(), key=lambda item: item.slot_id):
                if slot.service_lease_id is None and self._healthy(slot):
                    return self._lease(slot, reused=True)
            if len(self._slots) >= self.max_slots:
                raise SupervisorError("resource_unavailable: all model service slots are leased; retryable=true")
            return self._start_slot()

    def _start_slot(self) -> dict[str, Any]:
        active = self.cache.active()
        if not active:
            raise SupervisorError("persistent active model cache is missing")
        self.cache.verify(str(active["candidate_id"]), str(active["payload_sha256"]), full=False)
        candidate = self._candidate(str(active["candidate_id"]))
        gpu_count = 2 if candidate.get("profile") == "one-island" else 4
        self.runtime.host.discover_gpus()
        bundles = self.runtime.host.compound_gpu_bundles(gpu_count)
        if not bundles:
            raise SupervisorError("no runtime-discovered GPU bundle is available")
        slot_id = f"slot-{uuid.uuid4().hex[:12]}"
        reservation = None
        for candidate_bundle in bundles:
            reservation = self.runtime.host.reserve_service(
                project_root=self.repo_root, service_id=f"core4-local-model-{slot_id}",
                priority_class="active_local_delegation",
                resource_request={"schema_version": 1, "kind": "accelerator",
                                  "ids": candidate_bundle["resource_ids"],
                                  "exclusive_resources": candidate_bundle["exclusive_resources"]},
                pid=os.getpid(),
            )
            if reservation is not None:
                break
        if reservation is None:
            raise SupervisorError("resource_unavailable: no disjoint runtime-discovered GPU island is available; retryable=true")
        owner_id = str(reservation["owner_id"])
        gpu_uuids = [str(item).removeprefix("accelerator:") for item in reservation["resource_ids"]]
        server = self.profile["server"]
        port = self._free_port(int(server["base_port"]))
        binary = str(server["binary"])
        version = self._version(binary)
        service_profile = {
            "format": "CORE4-MODEL-SERVICE/2", "model_sha256": active["payload_sha256"],
            "allocated_gpu_uuids": gpu_uuids, "context_size": int(self.profile["experiment"]["initial_context"]),
            "gpu_layers": int(server.get("gpu_layers", 999)), "split_mode": str(server.get("split_mode", "layer")),
            "tensor_split": server.get("tensor_split"), "main_gpu": server.get("main_gpu"),
            "kv_cache_type_k": server.get("kv_cache_type_k"), "kv_cache_type_v": server.get("kv_cache_type_v"),
            "numa_policy": server.get("numa_policy"), "cpu_threads": server.get("cpu_threads"),
            "port": port, "startup_timeout_seconds": float(server["startup_timeout_seconds"]),
            "idle_ttl_seconds": self.ttl, "log_path": str(state_root() / f"llama-server-{slot_id}.log"),
        }
        key_values = {
            "model_id": active["candidate_id"], "model_sha256": active["payload_sha256"],
            "binary": str(Path(binary).resolve()), "binary_version": version, "gpu_uuids": gpu_uuids,
            "context_size": service_profile["context_size"], "split_mode": service_profile["split_mode"],
            "tensor_split": service_profile["tensor_split"], "main_gpu": service_profile["main_gpu"],
            "kv_cache_type_k": service_profile["kv_cache_type_k"], "kv_cache_type_v": service_profile["kv_cache_type_v"],
            "gpu_layers": service_profile["gpu_layers"], "numa_policy": service_profile["numa_policy"],
            "cpu_threads": service_profile["cpu_threads"],
        }
        _private_directory(state_root())
        log = Path(service_profile["log_path"])
        if log.exists() and log.stat().st_size > 4 * 1024 * 1024:
            rotated = log.with_suffix(".log.1")
            rotated.unlink(missing_ok=True)
            log.replace(rotated)
        try:
            cache_lease = self.cache.lease(str(active["candidate_id"]), str(active["payload_sha256"]), owner_id)
            model_path = cache_lease.__enter__()
            handle = self.service.start("llama", {
                "repo_root": str(self.repo_root), "model_path": str(model_path), "port": port,
                "service_profile": service_profile,
            })
            server_info = self.adapter.describe(handle)
            descriptor = {
                "format": "CORE4-MODEL-ENDPOINT/1", "base_url": server_info["base_url"] + "/v1",
                "model_id": active["candidate_id"], "model_sha256": active["payload_sha256"],
                "server_pid": server_info["pid"], "owner_id": owner_id, "gpu_uuids": gpu_uuids,
                "compatibility_key": self._compatibility(key_values),
            }
            slot = _ServiceSlot(
                slot_id=slot_id, handle=handle, endpoint_descriptor=descriptor,
                owner_id=owner_id, cache_lease=cache_lease, gpu_uuids=tuple(gpu_uuids),
                compatibility_key=str(descriptor["compatibility_key"]),
            )
            self._slots[slot_id] = slot
            return self._lease(slot, reused=False)
        except Exception:
            try:
                if "handle" in locals():
                    self.service.evict("llama", handle)
            finally:
                if "cache_lease" in locals():
                    cache_lease.__exit__(None, None, None)
                self.runtime.host.release(owner_id)
            raise

    def release(self, service_lease_id: str | None = None) -> dict[str, Any]:
        if service_lease_id is None:
            if len(self._leases) != 1:
                raise SupervisorError("unqualified release is ambiguous unless exactly one service lease exists")
            service_lease_id = next(iter(self._leases))
        slot_id = self._leases.pop(service_lease_id, None)
        if slot_id is None:
            raise SupervisorError("unknown or already released service lease")
        slot = self._slots.get(slot_id)
        if slot is None or slot.service_lease_id != service_lease_id:
            raise SupervisorError("service lease does not own the selected slot")
        slot.service_lease_id = None
        slot.state = "idle"
        slot.idle_since = time.monotonic()
        self.runtime.host.set_priority(slot.owner_id, "idle_model_residency")
        return {"released": True, "slot_id": slot_id, "service_lease_id": service_lease_id,
                "clients": len(self._leases), "idle_ttl_seconds": self.ttl}

    def preemption_status(self, service_lease_id: str | None = None) -> dict[str, Any]:
        if service_lease_id in self._preempted_leases:
            self._preempted_leases.discard(service_lease_id)
            return {"preempt_requested": True, "slot_ids": [], "draining": False,
                    "clients": len(self._leases), "preempted": True}
        slots = self._slots.values()
        if service_lease_id is not None:
            slot_id = self._leases.get(service_lease_id)
            slots = [] if slot_id is None else [self._slots[slot_id]]
        requested = [slot.slot_id for slot in slots if self.runtime.host.preempt_requested(slot.owner_id)]
        return {"preempt_requested": bool(requested), "slot_ids": requested,
                "draining": self.draining, "clients": len(self._leases)}

    def drain(self) -> dict[str, Any]:
        self.draining = True
        for slot in self._slots.values():
            slot.state = "draining"
            self.service.drain("llama", slot.handle)
        return {"draining": True, "clients": len(self._leases)}

    def _evict_slot(self, slot_id: str, *, preempted: bool = False) -> bool:
        slot = self._slots.pop(slot_id, None)
        if slot is None:
            return False
        if slot.service_lease_id is not None:
            self._leases.pop(slot.service_lease_id, None)
            if preempted:
                self._preempted_leases.add(slot.service_lease_id)
        try:
            self.service.drain("llama", slot.handle)
        finally:
            try:
                self.service.evict("llama", slot.handle)
            finally:
                slot.cache_lease.__exit__(None, None, None)
                self.runtime.host.release(slot.owner_id)
        return True

    def evict(self) -> dict[str, Any]:
        for slot_id in list(self._slots):
            self._evict_slot(slot_id)
        self.draining = False
        return {"evicted": True, "quiescent": True}

    def poll(self) -> None:
        for slot in list(self._slots.values()):
            self.runtime.host.heartbeat(slot.owner_id, pid=os.getpid())
            if self.runtime.host.preempt_requested(slot.owner_id):
                slot.state = "draining"
                self.service.drain("llama", slot.handle)
                self._evict_slot(slot.slot_id, preempted=True)
                continue
            if slot.service_lease_id is None and slot.idle_since is not None and self.ttl >= 0:
                if time.monotonic() - slot.idle_since >= self.ttl:
                    self._evict_slot(slot.slot_id)

    def close(self) -> None:
        self.evict()


class SupervisorServer:
    def __init__(self, backend: Backend, *, root: Path | None = None):
        self.backend = backend
        self.root = root or runtime_root()
        self.socket_path = self.root / "supervisor.sock"
        self.pid_path = self.root / "supervisor.pid"
        self.state_path = self.root / "supervisor-state.json"
        self.lock_path = self.root / "supervisor.lock"
        self.stopping = False

    def _dispatch(self, request: dict[str, Any]) -> dict[str, Any]:
        operation = request.get("operation")
        if operation == "status":
            return self.backend.status()
        if operation in {"warm", "acquire"}:
            return self.backend.warm()
        if operation == "release":
            return self.backend.release(request.get("service_lease_id"))
        if operation == "preemption-status":
            return self.backend.preemption_status(request.get("service_lease_id"))
        if operation == "drain":
            return self.backend.drain()
        if operation == "evict":
            return self.backend.evict()
        if operation == "stop":
            self.stopping = True
            return {**self.backend.evict(), "stopped": True}
        raise SupervisorError(f"unknown supervisor operation: {operation!r}")

    def serve(self) -> int:
        os.umask(0o077)
        _private_directory(self.root)
        lock_stream = self.lock_path.open("a+b")
        try:
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_stream.close()
            return 0
        if self.socket_path.exists():
            self.socket_path.unlink()
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(self.socket_path))
            self.socket_path.chmod(0o600)
            server.listen(8)
            server.settimeout(0.25)
            self.pid_path.write_text(str(os.getpid()) + "\n", encoding="ascii")
            self.pid_path.chmod(0o600)
            while not self.stopping:
                self.backend.poll()
                _atomic_json(self.state_path, self.backend.status())
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    continue
                with connection:
                    connection.settimeout(660)
                    data = b""
                    while b"\n" not in data and len(data) <= 64 * 1024:
                        block = connection.recv(4096)
                        if not block:
                            break
                        data += block
                    try:
                        request = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
                        response = {"ok": True, "data": self._dispatch(request)}
                    except Exception as exc:
                        response = {"ok": False, "error": str(exc)[:1000]}
                    try:
                        connection.sendall(json.dumps(response, separators=(",", ":")).encode("utf-8") + b"\n")
                    except (BrokenPipeError, ConnectionResetError):
                        # A short status probe may leave while a cold start is
                        # completing. The owner process and service pool remain valid.
                        pass
            return 0
        finally:
            self.backend.close()
            server.close()
            self.socket_path.unlink(missing_ok=True)
            self.pid_path.unlink(missing_ok=True)
            self.state_path.unlink(missing_ok=True)
            fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)
            lock_stream.close()


class SupervisorClient:
    def __init__(self, repo_root: str | Path, *, root: Path | None = None):
        self.repo_root = Path(repo_root).resolve()
        self.root = root or runtime_root()
        self.socket_path = self.root / "supervisor.sock"

    def _request(self, operation: str, *, timeout: float = 660, **parameters: Any) -> dict[str, Any]:
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(timeout)
        try:
            connection.connect(str(self.socket_path))
            connection.sendall(json.dumps({"operation": operation, **parameters}, separators=(",", ":")).encode("utf-8") + b"\n")
            data = b""
            while b"\n" not in data and len(data) <= 128 * 1024:
                block = connection.recv(4096)
                if not block:
                    break
                data += block
        finally:
            connection.close()
        response = json.loads(data.split(b"\n", 1)[0].decode("utf-8"))
        if not response.get("ok"):
            raise SupervisorError(str(response.get("error", "supervisor request failed")))
        return dict(response["data"])

    def _recover_stale(self) -> None:
        pid_path = self.root / "supervisor.pid"
        try:
            pid = int(pid_path.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            pid = 0
        if pid and _pid_alive(pid):
            return
        self.socket_path.unlink(missing_ok=True)
        pid_path.unlink(missing_ok=True)
        (self.root / "supervisor-state.json").unlink(missing_ok=True)

    def ensure_running(self) -> None:
        pid_path = self.root / "supervisor.pid"
        if self.socket_path.exists():
            try:
                if _pid_alive(int(pid_path.read_text(encoding="ascii").strip())):
                    return
            except (OSError, ValueError):
                pass
        try:
            self._request("status", timeout=1)
            return
        except (OSError, ValueError, json.JSONDecodeError, SupervisorError):
            self._recover_stale()
        _private_directory(self.root)
        skill_root = Path(__file__).resolve().parents[1]
        todo_root = Path(__file__).resolve().parents[2] / "todo-orchestrator"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, [str(skill_root), str(todo_root), environment.get("PYTHONPATH")]))
        log_root = state_root()
        _private_directory(log_root)
        stream = (log_root / "supervisor.log").open("a", encoding="utf-8")
        subprocess.Popen(
            [sys.executable, "-m", "local_worker.supervisor", "--serve", "--repo-root", str(self.repo_root)],
            stdin=subprocess.DEVNULL, stdout=stream, stderr=subprocess.STDOUT,
            start_new_session=True, close_fds=True, env=environment,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                self._request("status", timeout=1)
                return
            except (OSError, ValueError, json.JSONDecodeError, SupervisorError):
                time.sleep(0.05)
        raise SupervisorError("persistent model supervisor did not start")

    def request(self, operation: str, **parameters: Any) -> dict[str, Any]:
        if operation in {"warm", "acquire"}:
            self.ensure_running()
        elif not self.socket_path.exists():
            if operation == "status":
                return {"format": "CORE4-MODEL-SUPERVISOR/1", "running": False, "healthy": False}
            return {"running": False, "operation": operation}
        return self._request(operation, **parameters)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args(argv)
    if not args.serve:
        return 2
    return SupervisorServer(ProductionBackend(args.repo_root)).serve()


if __name__ == "__main__":
    raise SystemExit(main())
