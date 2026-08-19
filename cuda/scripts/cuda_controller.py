#!/usr/bin/env python3
"""One-call CUDA reconnaissance, measurement, background watches, and evidence retrieval."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import math
import os
import shutil
import signal
import sqlite3
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import re
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
TODO_ROOT = SKILL_ROOT.parent / "todo-orchestrator"
CTXPP = SKILL_ROOT.parent / "cpp-context-compiler" / "scripts" / "ctxpp"
if str(TODO_ROOT) not in sys.path:
    sys.path.insert(0, str(TODO_ROOT))

from todo_orchestrator.background.artifacts import file_digest  # noqa: E402
from todo_orchestrator.background.store import BackgroundStore  # noqa: E402
from todo_orchestrator.background.wake import wake_worker  # noqa: E402
from todo_orchestrator.config import project_paths  # noqa: E402

from cuda_guidance import retrieve  # noqa: E402

PARSER_VERSION = "cuda-controller/1"
MUTEX = SCRIPT_DIR / "with_benchmark_mutex.sh"


def emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def load_spec(value: str) -> dict[str, object]:
    text = sys.stdin.read() if value == "-" else Path(value).read_text(encoding="utf-8")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("spec must be a JSON object")
    return payload


def run(argv: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None,
        timeout: float = 10, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(argv, cwd=cwd, env=env, input=input_bytes, capture_output=True,
                              timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, b"", str(exc).encode())


def text_run(argv: list[str], *, cwd: Path | None = None, timeout: float = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return text_run(["git", "-C", str(root), *args], timeout=30)


def git_root(project: Path) -> Path:
    result = git(project, "rev-parse", "--show-toplevel")
    return Path(result.stdout.strip()).resolve() if result.returncode == 0 else project.resolve()


def tool_version(name: str) -> dict[str, object]:
    path = shutil.which(name)
    if not path:
        return {"path": None, "version": None}
    flag = "--version"
    result = text_run([path, flag], timeout=5)
    lines = (result.stdout + result.stderr).strip().splitlines()
    return {"path": path, "version": " | ".join(lines[:3])}


def _csv_query(fields: str) -> list[list[str]]:
    result = text_run(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"], timeout=5)
    if result.returncode != 0:
        return []
    return [[part.strip() for part in line.split(",")] for line in result.stdout.splitlines() if line.strip()]


def probe_gpus(*, dynamic: bool = True) -> list[dict[str, object]]:
    base_fields = "index,uuid,name,compute_cap,memory.total,pci.bus_id,driver_version"
    rows = _csv_query(base_fields)
    devices = []
    for row in rows:
        if len(row) < 7:
            continue
        index, gpu_uuid, name, capability, memory, bus, driver = row[:7]
        item: dict[str, object] = {
            "index": int(index), "uuid": gpu_uuid, "name": name,
            "compute_capability": capability, "memory_total_mib": int(float(memory)),
            "pci_bus_id": bus, "driver_version": driver,
        }
        devices.append(item)
    if dynamic:
        dynamic_rows = _csv_query("uuid,utilization.gpu,memory.free,temperature.gpu,clocks.sm,clocks_throttle_reasons.active")
        by_uuid = {row[0]: row for row in dynamic_rows if len(row) >= 6}
        for item in devices:
            values = by_uuid.get(str(item["uuid"]))
            if values:
                item.update(utilization_percent=float(values[1]), memory_free_mib=int(float(values[2])),
                            temperature_c=float(values[3]), clocks_sm_mhz=float(values[4]), throttle_reasons=values[5])
    return devices


def gpu_arch(capability: str) -> str:
    major = capability.split(".", 1)[0]
    return {"7": "volta", "8": "ampere", "9": "hopper", "10": "blackwell"}.get(major, "unknown")


def topology_tags(devices: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    result = text_run(["nvidia-smi", "topo", "-m"], timeout=5)
    tags = {str(item["uuid"]): {"pcie_root": str(item["pci_bus_id"]).rsplit(":", 1)[0]} for item in devices}
    if result.returncode != 0:
        return tags
    count = len(devices)
    parent = list(range(count))
    def find(value):
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value
    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[b] = a
    rows = {}
    for raw in result.stdout.splitlines():
        line = re.sub(r"\x1b\[[0-9;]*m", "", raw)
        fields = [field.strip() for field in line.split("\t")]
        if fields and re.fullmatch(r"GPU\d+", fields[0]):
            index = int(fields[0][3:])
            rows[index] = fields
            for peer, link in enumerate(fields[1:1 + count]):
                if link.startswith("NV"):
                    union(index, peer)
    domains = {root: number for number, root in enumerate(sorted({find(index) for index in range(count)}))}
    by_index = {int(item["index"]): str(item["uuid"]) for item in devices}
    for index, gpu_uuid in by_index.items():
        tags[gpu_uuid]["nvlink_domain"] = f"domain-{domains[find(index)]}"
        fields = rows.get(index, [])
        if len(fields) > count + 2:
            tags[gpu_uuid]["numa_node"] = fields[count + 2]
    return tags


def resource_facts(devices: list[dict[str, object]]) -> list[dict[str, object]]:
    topology = topology_tags(devices)
    return [{
        "id": f"accelerator:{item['uuid']}", "kind": "accelerator",
        "tags": {
            "vendor": "nvidia", "architecture": gpu_arch(str(item["compute_capability"])),
            "compute_capability": item["compute_capability"], "physical_index": item["index"],
            "model": item["name"], "memory_total_mib": item["memory_total_mib"],
            "pcie_bus_id": item["pci_bus_id"], **topology.get(str(item["uuid"]), {}),
        },
    } for item in devices]


def compute_processes() -> list[dict[str, object]]:
    result = text_run(["nvidia-smi", "--query-compute-apps=gpu_uuid,pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"], timeout=5)
    rows = []
    if result.returncode != 0:
        return rows
    for line in result.stdout.splitlines():
        fields = [item.strip() for item in line.split(",", 3)]
        if len(fields) == 4:
            rows.append({"uuid": fields[0], "pid": int(fields[1]), "process": fields[2], "used_memory_mib": fields[3]})
    return rows


def sample_devices(uuids: list[str], samples: int = 3, interval: float = 0.2) -> dict[str, object]:
    observations = []
    for index in range(samples):
        devices = [item for item in probe_gpus(dynamic=True) if item["uuid"] in uuids]
        processes = [item for item in compute_processes() if item["uuid"] in uuids and item["pid"] != os.getpid()]
        observations.append({"devices": devices, "foreign_processes": processes, "timestamp": time.time()})
        if index + 1 < samples:
            time.sleep(interval)
    contaminated = any(item["foreign_processes"] for item in observations)
    busy = any(any(float(gpu.get("utilization_percent", 0)) > 5.0 for gpu in item["devices"]) for item in observations)
    return {"samples": observations, "foreign_processes": contaminated, "busy": busy, "idle": not contaminated and not busy}


def project_inspect(project: Path) -> dict[str, object]:
    root = git_root(project)
    head = git(root, "rev-parse", "HEAD")
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all")
    cuda_files = []
    for suffix in ("*.cu", "*.cuh"):
        cuda_files.extend(path.relative_to(root).as_posix() for path in root.rglob(suffix)
                          if not any(part in {".git", "build", "_build", ".ctxpp"} for part in path.parts))
    compile_databases = [path.relative_to(root).as_posix() for path in root.rglob("compile_commands.json")
                         if ".git" not in path.parts][:8]
    topology = text_run(["nvidia-smi", "topo", "-m"], timeout=5)
    return {
        "schema_version": 1, "project_root": str(root),
        "git": {"head": head.stdout.strip() if head.returncode == 0 else None,
                "dirty": bool(status.stdout.strip()), "dirty_paths": status.stdout.splitlines()[:40]},
        "build": {
            "cmake": (root / "CMakeLists.txt").exists(), "meson": (root / "meson.build").exists(),
            "python": any((root / name).exists() for name in ("pyproject.toml", "setup.py")),
            "compile_databases": compile_databases,
        },
        "cuda_source": {"count": len(cuda_files), "sample": sorted(cuda_files)[:20]},
        "gpus": probe_gpus(dynamic=True), "topology": topology.stdout if topology.returncode == 0 else None,
        "tools": {name: tool_version(name) for name in ("nvcc", "nsys", "ncu", "compute-sanitizer", "cuda-gdb", "cuobjdump", "nvdisasm", "nvc++", "cmake")},
    }


def todo_database(root: Path) -> Path | None:
    try:
        return project_paths(root).db_file
    except Exception:
        return None


def todo_revision(root: Path) -> int:
    database = todo_database(root)
    if not database or not database.exists():
        return 0
    connection = sqlite3.connect(database)
    try:
        row = connection.execute("SELECT value FROM meta WHERE key='project_revision'").fetchone()
        return int(row[0]) if row else 0
    finally:
        connection.close()


def validate_watch_spec(spec: dict[str, object]) -> None:
    if int(spec.get("schema_version", 0)) != 1:
        raise ValueError("background spec schema_version must be 1")
    if not spec.get("project_root"):
        raise ValueError("background spec requires project_root")
    benchmark = spec.get("benchmark")
    if not isinstance(benchmark, dict) or not isinstance(benchmark.get("argv"), list) or not benchmark.get("argv"):
        raise ValueError("background spec requires benchmark.argv")
    if not isinstance(benchmark.get("correctness_argv"), list) or not benchmark.get("correctness_argv"):
        raise ValueError("background spec requires benchmark.correctness_argv")
    if not benchmark.get("metric") or benchmark.get("direction") not in {"minimize", "maximize"}:
        raise ValueError("background spec requires metric and minimize|maximize direction")
    for key in ("argv", "correctness_argv"):
        if not all(isinstance(item, str) for item in benchmark[key]):
            raise ValueError(f"benchmark.{key} must be structured argv strings")


def _path_matches(path: str, patterns: list[str]) -> bool:
    value = Path(path).as_posix().lstrip("./")
    return any(fnmatch.fnmatch(value, pattern) or value.startswith(pattern.rstrip("*/") + "/") for pattern in patterns)


def relevant_task(connection: sqlite3.Connection, task_id: str | None, watch: dict[str, object]) -> bool:
    if not task_id:
        return False
    ids = {str(item) for item in watch.get("task_ids", [])}
    prefixes = [str(item) for item in watch.get("task_prefixes", [])]
    if task_id in ids or any(task_id.startswith(prefix) for prefix in prefixes):
        return True
    patterns = [str(item) for item in watch.get("paths", [])]
    if patterns:
        scopes = [row[0] for row in connection.execute("SELECT path FROM ownership_scopes WHERE task_id=?", (task_id,))]
        return any(_path_matches(scope, patterns) or any(_path_matches(pattern.rstrip("*"), [scope]) for pattern in patterns) for scope in scopes)
    return not ids and not prefixes and not patterns and not watch.get("symbols")


def event_task(connection: sqlite3.Connection, event: sqlite3.Row) -> str | None:
    if event["event_type"].startswith("checkpoint."):
        row = connection.execute("SELECT task_id FROM checkpoints WHERE id=?", (event["entity_id"],)).fetchone()
        return str(row[0]) if row else None
    if event["event_type"] in {"task.completed", "task.handed_off", "continue.completed"}:
        return str(event["entity_id"]) if event["entity_id"] else None
    return None


def watched_scopes(connection: sqlite3.Connection, task_id: str | None, spec: dict[str, object]) -> list[str]:
    paths = [str(item) for item in spec.get("watch", {}).get("paths", [])]
    if task_id:
        paths.extend(str(row[0]) for row in connection.execute("SELECT path FROM ownership_scopes WHERE task_id=?", (task_id,)))
    return sorted(set(paths))


def _hash_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def create_snapshot(root: Path, artifact_root: Path, scopes: list[str], *, allow_dirty: bool) -> dict[str, object]:
    root = git_root(root)
    head_result = git(root, "rev-parse", "HEAD")
    if head_result.returncode != 0:
        return {"safe": False, "reason": "not-a-git-repository"}
    head = head_result.stdout.strip()
    runtime_exclusion = ":(exclude).todo-orchestrator/runtime/**"
    status = git(root, "status", "--porcelain=v1", "--untracked-files=all", "--", ".", runtime_exclusion)
    dirty = bool(status.stdout.strip())
    if dirty and not allow_dirty:
        return {"safe": False, "reason": "dirty-revision-advanced-before-snapshot", "commit": head}
    pathspecs = [*(scopes or ["."]), runtime_exclusion]
    patch_result = run(["git", "-C", str(root), "diff", "--binary", "HEAD", "--", *pathspecs], timeout=30)
    patch = patch_result.stdout if patch_result.returncode == 0 else b""
    untracked_result = git(root, "ls-files", "--others", "--exclude-standard")
    untracked = []
    for raw in untracked_result.stdout.splitlines() if untracked_result.returncode == 0 else []:
        if raw == ".todo-orchestrator/runtime" or raw.startswith(".todo-orchestrator/runtime/"):
            continue
        if not scopes or _path_matches(raw, scopes):
            source = root / raw
            if source.is_file():
                untracked.append((raw, file_digest(source)))
    fingerprint = hashlib.sha256(json.dumps({"head": head, "patch": _hash_bytes(patch), "untracked": untracked}, sort_keys=True).encode()).hexdigest()
    target = artifact_root / "snapshots" / fingerprint
    source_dir = target / "source"
    if not source_dir.exists():
        target.mkdir(parents=True, exist_ok=True)
        archive = run(["git", "-C", str(root), "archive", "--format=tar", head], timeout=60)
        if archive.returncode != 0:
            return {"safe": False, "reason": "git-archive-failed", "stderr": archive.stderr.decode(errors="replace")[-500:]}
        source_dir.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive.stdout), mode="r:") as bundle:
            bundle.extractall(source_dir, filter="data")
        if patch:
            applied = run(["git", "apply", "--whitespace=nowarn", "-"], cwd=source_dir, input_bytes=patch, timeout=30)
            if applied.returncode != 0:
                shutil.rmtree(target, ignore_errors=True)
                return {"safe": False, "reason": "patch-apply-failed", "stderr": applied.stderr.decode(errors="replace")[-500:]}
            (target / "tracked.patch").write_bytes(patch)
        for relative, _ in untracked:
            destination = source_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root / relative, destination)
    return {
        "safe": True, "project_root": str(root), "source_root": str(source_dir), "fingerprint": fingerprint,
        "commit": head, "dirty": dirty, "patch_hash": _hash_bytes(patch),
        "untracked": [{"path": path, "sha256": digest} for path, digest in untracked],
    }


def _resource_request(spec: dict[str, object]) -> dict[str, object]:
    policy = spec.get("policy", {})
    benchmark = spec.get("benchmark", {})
    explicit = [str(item) for item in benchmark.get("gpu_uuids", [])]
    count = int(benchmark.get("gpus", 1))
    count = min(count, int(policy.get("max_background_gpus", 4)))
    return {
        "kind": "accelerator", "ids": [f"accelerator:{item}" for item in explicit],
        "count": 0 if explicit else count, "cpu_heavy": bool(benchmark.get("cpu_heavy", False)),
        "cpu_threads": int(benchmark.get("background_cpu_threads", 0) or 0),
        "ram_bytes": int(benchmark.get("background_ram_bytes", 0) or 0),
        "tags": ({"architecture": str(benchmark["architecture"])} if benchmark.get("architecture") else {}),
    }


def stage_argv(project: Path, watch_id: str, kind: str, snapshot: dict[str, object]) -> list[str]:
    return [sys.executable, str(Path(__file__).resolve()), "_stage", "--project", str(project), "--watch-id", watch_id,
            "--kind", kind, "--snapshot", json.dumps(snapshot, separators=(",", ":"))]


def queue_revision(store: BackgroundStore, watch: dict[str, object], snapshot: dict[str, object], *,
                   task_id: str | None, revision: int, initial: bool = False) -> list[str]:
    if not snapshot.get("safe"):
        store.set_meta(f"skip:{watch['id']}:{revision}", {"reason": snapshot.get("reason"), "task_id": task_id})
        return []
    fingerprint = str(snapshot["fingerprint"])
    if store.get_meta(f"queued:{watch['id']}:{revision}:{fingerprint}"):
        return []
    request = _resource_request(watch["spec"])
    common = {
        "watch_id": watch["id"], "cwd": snapshot["source_root"], "resources": request,
        "source_fingerprint": fingerprint, "task_id": task_id, "todo_revision": revision,
        "snapshot": snapshot, "retry_limit": 1,
    }
    correctness, created = store.enqueue({**common, "kind": "correctness", "priority": 40,
        "argv": stage_argv(store.project_root, str(watch["id"]), "correctness", snapshot),
        "dedup_key": f"{watch['id']}:{fingerprint}:correctness"})
    benchmark, _ = store.enqueue({**common, "kind": "benchmark", "priority": 40,
        "argv": stage_argv(store.project_root, str(watch["id"]), "benchmark", snapshot),
        "dedup_key": f"{watch['id']}:{fingerprint}:benchmark"}, [correctness])
    jobs = [correctness, benchmark]
    if initial and bool(watch["spec"].get("policy", {}).get("initial_characterization", True)):
        nsys, _ = store.enqueue({**common, "kind": "nsys", "priority": 50,
            "argv": stage_argv(store.project_root, str(watch["id"]), "nsys", snapshot),
            "dedup_key": f"{watch['id']}:{fingerprint}:nsys", "retry_limit": 0}, [benchmark])
        ncu, _ = store.enqueue({**common, "kind": "ncu", "priority": 50,
            "argv": stage_argv(store.project_root, str(watch["id"]), "ncu", snapshot),
            "dedup_key": f"{watch['id']}:{fingerprint}:ncu", "retry_limit": 0}, [nsys])
        jobs.extend((nsys, ncu))
    for position, raw_candidate in enumerate(watch["spec"].get("candidates", [])):
        if not isinstance(raw_candidate, dict):
            continue
        candidate = dict(raw_candidate)
        candidate_id = str(candidate.get("id") or f"candidate-{position}")
        candidate_snapshot = {**snapshot, "_candidate": {**candidate, "id": candidate_id}}
        candidate_common = {**common, "snapshot": candidate_snapshot}
        dependency = benchmark
        if candidate.get("build_argv"):
            dependency, _ = store.enqueue({**candidate_common, "kind": "candidate-build", "priority": 50,
                "argv": stage_argv(store.project_root, str(watch["id"]), "candidate-build", candidate_snapshot),
                "dedup_key": f"{watch['id']}:{fingerprint}:{candidate_id}:build"}, [correctness])
            jobs.append(dependency)
        candidate_correctness, _ = store.enqueue({**candidate_common, "kind": "candidate-correctness", "priority": 50,
            "argv": stage_argv(store.project_root, str(watch["id"]), "candidate-correctness", candidate_snapshot),
            "dedup_key": f"{watch['id']}:{fingerprint}:{candidate_id}:correctness"}, [dependency])
        candidate_benchmark, _ = store.enqueue({**candidate_common, "kind": "candidate-benchmark", "priority": 50,
            "argv": stage_argv(store.project_root, str(watch["id"]), "candidate-benchmark", candidate_snapshot),
            "dedup_key": f"{watch['id']}:{fingerprint}:{candidate_id}:benchmark"}, [candidate_correctness, benchmark])
        jobs.extend((candidate_correctness, candidate_benchmark))
    store.set_meta(f"queued:{watch['id']}:{revision}:{fingerprint}", jobs)
    store.set_meta(f"last-relevant:{watch['id']}", {"task_id": task_id, "revision": revision, "snapshot": snapshot})
    return jobs


def sync_watch(project: Path, watch_id: str) -> dict[str, object]:
    store = BackgroundStore(project)
    watch = store.watch(watch_id)
    if not watch or watch["state"] != "armed":
        return {"queued": 0}
    database = todo_database(project)
    if not database or not database.exists():
        return {"queued": 0, "reason": "no-todo-event-stream"}
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    queued = []
    try:
        events = connection.execute("SELECT * FROM events WHERE revision>? ORDER BY revision", (watch["event_cursor"],)).fetchall()
        relevant_positions = []
        for event in events:
            task_id = event_task(connection, event)
            if relevant_task(connection, task_id, watch["spec"].get("watch", {})):
                relevant_positions.append(event["revision"])
        for event in events:
            revision = int(event["revision"])
            task_id = event_task(connection, event)
            is_relevant = relevant_task(connection, task_id, watch["spec"].get("watch", {}))
            if is_relevant and event["event_type"] in {"task.completed", "task.handed_off", "checkpoint.reach"}:
                later_relevant = any(value > revision for value in relevant_positions)
                scopes = watched_scopes(connection, task_id, watch["spec"])
                snapshot = create_snapshot(project, store.paths.artifacts, scopes, allow_dirty=not later_relevant)
                prior = store.get_meta(f"last-relevant:{watch_id}", {})
                if snapshot.get("fingerprint") != prior.get("snapshot", {}).get("fingerprint"):
                    queued.extend(queue_revision(store, watch, snapshot, task_id=task_id, revision=revision))
            elif is_relevant and event["event_type"] == "continue.completed":
                prior = store.get_meta(f"last-relevant:{watch_id}")
                if prior:
                    queued.extend(queue_revision(store, watch, prior["snapshot"], task_id=prior.get("task_id"), revision=int(prior["revision"])))
            store.update_watch_cursor(watch_id, revision)
    finally:
        connection.close()
    return {"queued": len(set(queued)), "job_ids": sorted(set(queued))}


def _allocated_gpus() -> tuple[list[str], list[int]]:
    ids = [item for item in os.environ.get("TODO_BACKGROUND_RESOURCE_IDS", "").split(",") if item]
    uuids = [item.split("accelerator:", 1)[1] for item in ids if item.startswith("accelerator:")]
    mapping = {str(item["uuid"]): int(item["index"]) for item in probe_gpus(dynamic=False)}
    return uuids, [mapping[item] for item in uuids if item in mapping]


def _command_environment(indices: list[int], uuids: list[str], background: bool) -> dict[str, str]:
    environment = os.environ.copy()
    if indices:
        environment["CUDA_VISIBLE_DEVICES"] = ",".join(str(item) for item in indices)
    if background:
        environment["CUDA_BENCHMARK_COORDINATION_MODE"] = "background"
        environment["CUDA_BACKGROUND_GPU_UUIDS"] = ",".join(uuids)
    return environment


def _capture(argv: list[str], cwd: Path, environment: dict[str, str], output_dir: Path, label: str, timeout: float) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / f"{label}.stdout.txt"
    stderr_path = output_dir / f"{label}.stderr.txt"
    started = time.monotonic()
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(argv, cwd=cwd, env=environment, stdout=stdout, stderr=stderr, start_new_session=False)
        try:
            returncode = process.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            returncode, timed_out = process.returncode, True
    return {"argv": argv, "returncode": returncode, "timeout": timed_out,
            "elapsed_seconds": time.monotonic() - started, "stdout": str(stdout_path), "stderr": str(stderr_path)}


def _load_json_output(path: Path) -> object | None:
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            for line in reversed(text.splitlines()):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    continue
    except OSError:
        pass
    return None


def _metric(payload: object, path: str) -> float:
    value = payload
    for part in path.split("."):
        if isinstance(value, dict):
            value = value[part]
        elif isinstance(value, list):
            value = value[int(part)]
        else:
            raise KeyError(path)
    return float(value)


def _robust(values: list[float]) -> dict[str, object]:
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    mad = statistics.median(deviations)
    result: dict[str, object] = {"median": median, "mad": mad, "values": values, "included": list(range(len(values))), "excluded": []}
    if len(values) >= 5:
        half = 1.96 * 1.4826 * mad / math.sqrt(len(values))
        result["confidence_interval_approx_95"] = [median - half, median + half]
    return result


def provenance(project: Path, snapshot: dict[str, object], argv: list[str], devices: list[dict[str, object]], spec: dict[str, object]) -> dict[str, object]:
    executable = Path(argv[0]) if argv else Path("")
    if argv and not executable.is_absolute():
        located = shutil.which(argv[0])
        executable = Path(located) if located else project / argv[0]
    inputs = []
    for raw in spec.get("inputs", []):
        path = (project / str(raw)).resolve()
        if path.is_file():
            inputs.append({"path": str(path), "sha256": file_digest(path)})
    relevant_environment = {
        key: value for key, value in os.environ.items()
        if key.startswith(("CUDA_", "NCCL_", "CUBLAS_", "CUDNN_", "OMP_"))
    }
    return {
        "project_root": str(project), "source": snapshot,
        "binary": {"path": str(executable) if argv else None, "sha256": file_digest(executable) if argv and executable.is_file() else None},
        "argv": argv, "inputs": inputs, "gpus": devices,
        "tools": {name: tool_version(name) for name in ("nvcc", "nsys", "ncu")},
        "environment": relevant_environment, "parser_version": PARSER_VERSION, "timestamp": time.time(),
    }


def _benchmark(spec: dict[str, object], cwd: Path, env: dict[str, str], output_dir: Path,
               *, background: bool, wrap_mutex: bool = True) -> dict[str, object]:
    benchmark = spec["benchmark"]
    command = [str(item).replace("{snapshot}", str(cwd)) for item in benchmark["argv"]]
    repetitions = int(benchmark.get("repetitions", 5))
    warmups = int(benchmark.get("warmups", 1))
    timeout = float(benchmark.get("timeout", 3600))
    records = []
    for index in range(warmups + repetitions):
        argv = [str(MUTEX), "--label", f"cuda-controller-{index}", "--", *command] if wrap_mutex else command
        record = _capture(argv, cwd, env, output_dir, f"benchmark-{index}", timeout)
        record["warmup"] = index < warmups
        payload = _load_json_output(Path(record["stdout"]))
        try:
            record["metric"] = _metric(payload, str(benchmark["metric"]))
        except (KeyError, TypeError, ValueError):
            record["metric"] = None
        records.append(record)
        if record["returncode"] != 0:
            break
    included = [float(item["metric"]) for item in records if not item["warmup"] and item["returncode"] == 0 and item["metric"] is not None]
    valid = len(included) == repetitions
    return {"valid": valid, "records": records, "statistics": _robust(included) if included else None}


def _classify_benchmark(store: BackgroundStore, watch_id: str, spec: dict[str, object], outcome: dict[str, object], fingerprint: str) -> dict[str, object]:
    benchmark = spec["benchmark"]
    if not outcome["valid"]:
        return {**outcome, "status": "failed", "classification": "correctness-or-measurement-failure", "severity": 100, "valid": False,
                "parser_version": PARSER_VERSION, "source_fingerprint": fingerprint}
    current = float(outcome["statistics"]["median"])
    baseline_key = f"baseline:{watch_id}"
    baseline = store.get_meta(baseline_key)
    direction = str(benchmark["direction"])
    threshold = float(benchmark.get("practical_regression_percent", 2.0))
    classification, severity, delta = "healthy", 0, None
    if baseline and baseline.get("valid"):
        prior = float(baseline["median"])
        delta = ((current - prior) / abs(prior) * 100.0) if direction == "minimize" else ((prior - current) / abs(prior) * 100.0)
        if delta > threshold:
            classification, severity = "material-regression", 90
    target = benchmark.get("target")
    if target is not None:
        missed = current > float(target) if direction == "minimize" else current < float(target)
        if missed and severity < 80:
            classification, severity = "target-missed", 80
    mad = float(outcome["statistics"]["mad"])
    if current and mad / abs(current) > 0.05 and severity < 70:
        classification, severity = "severe-variance", 70
    result = {**outcome, "status": "succeeded", "classification": classification, "severity": severity,
              "metric": benchmark["metric"], "direction": direction, "comparison_percent": delta,
              "baseline": baseline, "parser_version": PARSER_VERSION, "source_fingerprint": fingerprint}
    if not baseline:
        store.set_meta(baseline_key, {"valid": True, "median": current, "source_fingerprint": fingerprint})
    return result


def background_stage(project: Path, watch_id: str, kind: str, snapshot: dict[str, object]) -> dict[str, object]:
    store = BackgroundStore(project)
    watch = store.watch(watch_id)
    if not watch:
        return {"valid": False, "status": "failed", "classification": "watch-missing", "severity": 0}
    spec = watch["spec"]
    candidate = snapshot.get("_candidate", {})
    benchmark = {**spec["benchmark"]}
    if isinstance(candidate, dict):
        for key in ("argv", "correctness_argv", "metric", "direction", "target", "practical_regression_percent"):
            if key in candidate:
                benchmark[key] = candidate[key]
    effective_spec = {**spec, "benchmark": benchmark}
    cwd = Path(str(snapshot["source_root"]))
    artifact_dir = Path(os.environ.get("TODO_BACKGROUND_ARTIFACT_DIR", store.paths.artifacts / "unbound")) / "cuda"
    uuids, indices = _allocated_gpus()
    before = sample_devices(uuids) if uuids else {"idle": True, "samples": []}
    required_free = int(spec["benchmark"].get("gpu_memory_headroom_mib", 0) or 0)
    memory_low = required_free and any(
        int(gpu.get("memory_free_mib", 0)) < required_free
        for observation in before.get("samples", []) for gpu in observation.get("devices", [])
    )
    if uuids and (not before["idle"] or memory_low):
        return {"valid": False, "contaminated": True, "status": "skipped", "classification": "resource-busy", "severity": 0,
                "resource_samples": before, "parser_version": PARSER_VERSION}
    env = _command_environment(indices, uuids, background=True)
    if isinstance(candidate, dict):
        env.update({str(key): str(value) for key, value in dict(candidate.get("env", {})).items()})
    fingerprint = str(snapshot["fingerprint"])
    base_kind = kind.removeprefix("candidate-")
    if base_kind == "build":
        command = [str(item).replace("{snapshot}", str(cwd)) for item in candidate.get("build_argv", [])]
        record = _capture(command, cwd, env, artifact_dir, "candidate-build", float(candidate.get("build_timeout", 3600)))
        valid = bool(command) and record["returncode"] == 0
        result = {"valid": valid, "status": "succeeded" if valid else "failed",
                  "classification": "candidate-built" if valid else "candidate-build-failure", "severity": 0,
                  "record": record, "parser_version": PARSER_VERSION, "source_fingerprint": fingerprint}
    elif base_kind == "correctness":
        command = [str(item).replace("{snapshot}", str(cwd)) for item in benchmark["correctness_argv"]]
        record = _capture(command, cwd, env, artifact_dir, "correctness", float(benchmark.get("correctness_timeout", 1800)))
        valid = record["returncode"] == 0
        result = {"valid": valid, "status": "succeeded" if valid else "failed",
                  "classification": "healthy" if valid else "correctness-failure", "severity": 0 if valid else 100,
                  "record": record, "parser_version": PARSER_VERSION, "source_fingerprint": fingerprint}
    elif base_kind == "benchmark":
        outcome = _benchmark(effective_spec, cwd, env, artifact_dir, background=True)
        result = _classify_benchmark(store, watch_id, effective_spec, outcome, fingerprint)
        if isinstance(candidate, dict) and candidate:
            result["candidate_id"] = candidate.get("id")
        if result["severity"] >= 70:
            request = _resource_request(spec)
            common = {"watch_id": watch_id, "cwd": str(cwd), "resources": request, "source_fingerprint": fingerprint,
                      "snapshot": snapshot, "priority": 50, "retry_limit": 0}
            limit = int(spec.get("policy", {}).get("max_deep_profiles_per_revision", 2))
            for profile_kind in ("nsys", "ncu")[:max(0, min(2, limit))]:
                store.enqueue({**common, "kind": profile_kind, "argv": stage_argv(project, watch_id, profile_kind, snapshot),
                               "dedup_key": f"{watch_id}:{fingerprint}:{candidate.get('id', 'base')}:{profile_kind}"})
    elif base_kind in {"nsys", "ncu"}:
        wrapper = SCRIPT_DIR / f"profile_{base_kind}.sh"
        command = [str(item).replace("{snapshot}", str(cwd)) for item in benchmark["argv"]]
        output = artifact_dir / base_kind
        argv = [str(wrapper), "--out-dir", str(output), "--label", "run", "--", *command]
        record = _capture(argv, cwd, env, artifact_dir, base_kind, float(benchmark.get("profile_timeout", 3600)))
        summary_path = output / "run" / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.exists() else None
        result = {"valid": record["returncode"] == 0 and summary is not None, "status": "succeeded" if record["returncode"] == 0 else "failed",
                  "classification": "profile-observation", "severity": 0, "record": record, "summary": summary,
                  "raw_report_root": str(output / "run"), "parser_version": PARSER_VERSION, "source_fingerprint": fingerprint}
    else:
        result = {"valid": False, "status": "failed", "classification": "unknown-stage", "severity": 0}
    after = sample_devices(uuids) if uuids else {"idle": True, "samples": []}
    if after.get("foreign_processes"):
        result.update(valid=False, contaminated=True, status="skipped", classification="measurement-contaminated", severity=0)
    result["resource_samples"] = {"before": before, "after": after}
    command = candidate.get("build_argv", []) if base_kind == "build" else benchmark["correctness_argv"] if base_kind == "correctness" else benchmark["argv"]
    result["provenance"] = provenance(project, snapshot, [str(item) for item in command], probe_gpus(dynamic=False), benchmark)
    return result


def _ctxpp_context(spec: dict[str, object], project: Path) -> dict[str, object] | None:
    request = spec.get("context")
    if not isinstance(request, dict) or not request.get("target") or not (project / ".ctxpp.toml").exists():
        return None
    target = str(request["target"])
    intent = str(request.get("intent", "performance"))
    budget = int(request.get("budget", 1200))
    process = text_run([str(CTXPP), "--root", str(project), "--json", "slice", target, "--intent", intent, "--budget", str(budget)], timeout=60)
    if process.returncode == 0:
        try:
            return {"provider": "cpp-context-compiler", "slice": json.loads(process.stdout)}
        except json.JSONDecodeError:
            pass
    fallback = request.get("cuda_source")
    if fallback:
        split = text_run([sys.executable, str(SCRIPT_DIR / "split_cuda_translation_unit.py"), str(project / str(fallback)), "--list-kernels"], timeout=60)
        return {"provider": "cuda-tu-splitter", "fallback_reason": (process.stderr or "semantic retrieval failed")[-500:], "result": split.stdout, "returncode": split.returncode}
    return {"provider": "canonical-source", "fallback_reason": (process.stderr or "semantic retrieval failed")[-500:]}


def _foreground_capture(argv: list[str], cwd: Path, env: dict[str, str], output_dir: Path, timeout: float) -> dict[str, object]:
    return _capture(argv, cwd, env, output_dir, "foreground", timeout)


def _recipe(spec: dict[str, object], artifact_dir: Path) -> tuple[list[str], bool]:
    recipe = str(spec.get("recipe", "baseline"))
    argv = [str(item) for item in spec.get("argv", [])]
    if not argv:
        raise ValueError("run spec requires argv")
    if recipe == "baseline":
        return [str(MUTEX), "--label", "cuda-controller-foreground", "--", *argv], False
    if recipe in {"nsys", "ncu"}:
        return [str(SCRIPT_DIR / f"profile_{recipe}.sh"), "--out-dir", str(artifact_dir / recipe), "--label", "run", "--", *argv], False
    if recipe == "debug-crash":
        return [str(SCRIPT_DIR / "debug_crash.sh"), "--out-dir", str(artifact_dir / "debug"), "--label", "run", "--", *argv], False
    if recipe == "compute-sanitizer":
        return [str(SCRIPT_DIR / "debug_compute_sanitizer.sh"), "--out-dir", str(artifact_dir / "sanitizer"), "--label", "run", "--", *argv], False
    if recipe == "cuda-gdb":
        return [str(SCRIPT_DIR / "debug_cuda_gdb.sh"), "--out-dir", str(artifact_dir / "cuda-gdb"), "--label", "run", "--", *argv], False
    if recipe == "ptx-sass":
        if not spec.get("explicit_ptx_sass"):
            raise ValueError("PTX/SASS requires explicit_ptx_sass=true")
        return [str(SCRIPT_DIR / "dump_ptx_hotspot.sh"), "--out-dir", str(artifact_dir / "ptx"), *argv], False
    raise ValueError(f"unknown recipe: {recipe}")


def foreground_run(spec: dict[str, object]) -> dict[str, object]:
    project = git_root(Path(str(spec.get("project_root", "."))))
    store = BackgroundStore(project)
    devices = probe_gpus(dynamic=True)
    store.upsert_resources(resource_facts(devices))
    resources = spec.get("resources", {})
    requested = [str(item) for item in resources.get("gpu_uuids", [])] if isinstance(resources, dict) else []
    count = int(resources.get("gpus", 1)) if isinstance(resources, dict) else 1
    if not requested:
        requested = [str(item["uuid"]) for item in devices[:count]]
    resource_ids = [f"accelerator:{item}" for item in requested]
    intent = store.foreground_intent(resource_ids)
    marker = Path(os.environ.get("CUDA_BENCHMARK_FOREGROUND_INTENT_PATH", os.environ.get("CUDA_V100_BENCHMARK_MUTEX_PATH", f"{os.environ.get('TMPDIR', '/tmp')}/cuda_v100_benchmark.lock") + ".foreground-intent"))
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(f"controller:{intent}\n", encoding="utf-8")
    try:
        deadline = time.monotonic() + float(spec.get("preempt_grace_seconds", 5))
        while store.running_conflicts(resource_ids) and time.monotonic() < deadline:
            time.sleep(0.1)
        if store.running_conflicts(resource_ids) or not store.reserve_foreground(intent, resource_ids):
            return {"ok": False, "code": "foreground_resource_contention"}
        sample = sample_devices(requested)
        if requested and sample["foreign_processes"]:
            return {"ok": False, "code": "foreign_gpu_activity", "resources": sample}
        snapshot = create_snapshot(project, store.paths.artifacts, [str(item) for item in spec.get("paths", [])], allow_dirty=True)
        if not snapshot.get("safe"):
            return {"ok": False, "code": "snapshot_failed", "reason": snapshot.get("reason")}
        run_id = str(uuid.uuid4())
        artifact_dir = store.paths.artifacts / "foreground" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        mapping = {str(item["uuid"]): int(item["index"]) for item in devices}
        indices = [mapping[item] for item in requested if item in mapping]
        environment = _command_environment(indices, requested, background=False)
        environment["CUDA_BENCHMARK_FOREGROUND_INTENT_HELD"] = "1"
        environment["CUDA_BENCHMARK_FOREGROUND_INTENT_PATH"] = str(marker)
        correctness = None
        if spec.get("correctness_argv"):
            correctness = _foreground_capture([str(item) for item in spec["correctness_argv"]], project, environment, artifact_dir, float(spec.get("correctness_timeout", 1800)))
            if correctness["returncode"] != 0:
                result = {"status": "failed", "valid": False, "classification": "correctness-failure", "severity": 100,
                          "correctness": correctness, "parser_version": PARSER_VERSION}
                _, evidence_id = store.record_external_result(kind="foreground-correctness", argv=spec["correctness_argv"], cwd=str(project), source_fingerprint=snapshot.get("fingerprint"), snapshot=snapshot, result=result,
                    artifacts=[{"kind": "stdout", "path": correctness["stdout"], "content_hash": file_digest(Path(correctness["stdout"]))}, {"kind": "stderr", "path": correctness["stderr"], "content_hash": file_digest(Path(correctness["stderr"]))}])
                return {"ok": False, "finding": f"CORRECTNESS FAILURE: foreground check failed. [e:{evidence_id}]", "evidence_id": evidence_id}
        argv, _ = _recipe(spec, artifact_dir)
        benchmark_outcome = None
        if str(spec.get("recipe", "baseline")) == "baseline" and spec.get("metric"):
            benchmark_spec = {"benchmark": {
                "argv": [str(item) for item in spec["argv"]], "metric": spec["metric"],
                "direction": spec.get("direction", "minimize"), "warmups": spec.get("warmups", 1),
                "repetitions": spec.get("repetitions", 5), "timeout": spec.get("timeout", 3600),
            }}
            benchmark_outcome = _benchmark(benchmark_spec, project, environment, artifact_dir, background=False)
            record = {"argv": argv, "returncode": 0 if benchmark_outcome["valid"] else 1,
                      "statistics": benchmark_outcome["statistics"], "records": benchmark_outcome["records"]}
        else:
            record = _foreground_capture(argv, project, environment, artifact_dir, float(spec.get("timeout", 3600)))
        after = sample_devices(requested)
        valid = record["returncode"] == 0 and not after.get("foreign_processes")
        result = {"status": "succeeded" if valid else "failed", "valid": valid,
                  "classification": "decision-result" if valid else "measurement-failure", "severity": 0 if valid else 90,
                  "record": record, "correctness": correctness, "resource_samples": {"before": sample, "after": after},
                  "context": _ctxpp_context(spec, project), "benchmark": benchmark_outcome,
                  "provenance": provenance(project, snapshot, [str(item) for item in spec["argv"]], [item for item in devices if item["uuid"] in requested], spec),
                  "parser_version": PARSER_VERSION}
        artifacts = []
        if benchmark_outcome:
            for item in benchmark_outcome["records"]:
                artifacts.extend([{"kind": "stdout", "path": item["stdout"], "content_hash": file_digest(Path(item["stdout"]))},
                                  {"kind": "stderr", "path": item["stderr"], "content_hash": file_digest(Path(item["stderr"]))}])
        else:
            artifacts = [{"kind": "stdout", "path": record["stdout"], "content_hash": file_digest(Path(record["stdout"]))},
                         {"kind": "stderr", "path": record["stderr"], "content_hash": file_digest(Path(record["stderr"]))}]
        _, evidence_id = store.record_external_result(kind=f"foreground-{spec.get('recipe', 'baseline')}", argv=argv, cwd=str(project), source_fingerprint=snapshot.get("fingerprint"), snapshot=snapshot, result=result, artifacts=artifacts)
        return {"ok": valid, "status": result["status"], "classification": result["classification"],
                "returncode": record["returncode"], "evidence_id": evidence_id,
                "message": "No action-worthy result; evidence stored." if valid else f"MEASUREMENT FAILURE: foreground recipe failed. [e:{evidence_id}]"}
    finally:
        store.clear_foreground(intent)
        try:
            if marker.read_text(encoding="utf-8").strip() == f"controller:{intent}":
                marker.unlink()
        except OSError:
            pass


def arm_background(spec: dict[str, object]) -> dict[str, object]:
    validate_watch_spec(spec)
    project = git_root(Path(str(spec["project_root"])))
    spec = dict(spec)
    spec["project_root"] = str(project)
    store = BackgroundStore(project)
    devices = probe_gpus(dynamic=True)
    store.upsert_resources(resource_facts(devices))
    store.set_meta("cuda-machine-facts", {"gpus": devices, "tools": {name: tool_version(name) for name in ("nvcc", "nsys", "ncu")}})
    runtime = dict(spec.get("_runtime", {}))
    provisional = str(spec.get("watch_id") or hashlib.sha256(json.dumps({"root": str(project), "watch": spec.get("watch", {})}, sort_keys=True).encode()).hexdigest()[:24])
    runtime["event_handler_argv"] = [sys.executable, str(Path(__file__).resolve()), "_sync-watch", "--project", str(project), "--watch-id", provisional]
    spec["watch_id"] = provisional
    spec["_runtime"] = runtime
    cursor = todo_revision(project)
    watch_id = store.arm_watch(spec, event_cursor=cursor)
    watch = store.watch(watch_id)
    initial_jobs = []
    if bool(spec.get("policy", {}).get("initial_characterization", True)):
        snapshot = create_snapshot(project, store.paths.artifacts, [str(item) for item in spec.get("watch", {}).get("paths", [])], allow_dirty=True)
        initial_jobs = queue_revision(store, watch, snapshot, task_id=None, revision=cursor, initial=True)
    wake_worker(project)
    return {"schema_version": 1, "watch_id": watch_id, "state": "armed", "initial_jobs_queued": len(initial_jobs)}


def control_background(project: Path, state: str) -> dict[str, object]:
    store = BackgroundStore(git_root(project), create=False)
    if not store.paths.database.exists():
        return {"schema_version": 1, "state": "absent"}
    store = BackgroundStore(project)
    if state == "stopped":
        store.cancel_background()
    count = store.set_watch_state(state)
    if state == "armed":
        wake_worker(project)
    return {"schema_version": 1, "state": state, "watches": count}


def evidence(project: Path, identifier: str, focus: str) -> dict[str, object]:
    store = BackgroundStore(git_root(project), create=False)
    if not store.paths.database.exists():
        return {"evidence": None}
    store = BackgroundStore(project)
    item = store.result(identifier)
    if item:
        return {"evidence": item}
    findings = store.visible_findings(focus=focus, limit=3)
    if not findings:
        return {"message": "No action-worthy result; evidence stored.", "findings": []}
    return {"findings": findings}


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect"); inspect.add_argument("--project", required=True); inspect.add_argument("--json", action="store_true")
    background = sub.add_parser("background"); background_sub = background.add_subparsers(dest="background_command", required=True)
    arm = background_sub.add_parser("arm"); arm.add_argument("--spec", required=True); arm.add_argument("--json", action="store_true")
    for name in ("pause", "resume", "stop"):
        item = background_sub.add_parser(name); item.add_argument("--project", required=True); item.add_argument("--json", action="store_true")
    execute = sub.add_parser("run"); execute.add_argument("--spec", required=True); execute.add_argument("--json", action="store_true")
    ev = sub.add_parser("evidence"); ev.add_argument("id"); ev.add_argument("--project", default="."); ev.add_argument("--focus", default=""); ev.add_argument("--json", action="store_true")
    guide = sub.add_parser("guide"); guide.add_argument("--query", required=True); guide.add_argument("--json", action="store_true")
    sync = sub.add_parser("_sync-watch"); sync.add_argument("--project", required=True); sync.add_argument("--watch-id", required=True)
    stage = sub.add_parser("_stage"); stage.add_argument("--project", required=True); stage.add_argument("--watch-id", required=True); stage.add_argument("--kind", required=True); stage.add_argument("--snapshot", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "inspect":
            payload = project_inspect(Path(args.project))
        elif args.command == "background":
            if args.background_command == "arm":
                payload = arm_background(load_spec(args.spec))
            else:
                state = {"pause": "paused", "resume": "armed", "stop": "stopped"}[args.background_command]
                payload = control_background(Path(args.project), state)
        elif args.command == "run":
            payload = foreground_run(load_spec(args.spec))
        elif args.command == "evidence":
            payload = evidence(Path(args.project), args.id, args.focus)
        elif args.command == "guide":
            payload = retrieve(SKILL_ROOT, args.query)
        elif args.command == "_sync-watch":
            payload = sync_watch(Path(args.project), args.watch_id)
        else:
            payload = background_stage(Path(args.project), args.watch_id, args.kind, json.loads(args.snapshot))
        emit(payload)
        if isinstance(payload, dict) and payload.get("contaminated"):
            return 75
        if args.command == "_stage" and isinstance(payload, dict) and payload.get("valid") is False and payload.get("status") == "failed":
            return 1
        return 0 if not isinstance(payload, dict) or payload.get("ok", True) is not False else 1
    except Exception as exc:
        emit({"ok": False, "code": "cuda_controller_error", "message": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
