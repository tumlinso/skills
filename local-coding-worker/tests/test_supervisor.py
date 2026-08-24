from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.supervisor import ProductionBackend, SupervisorClient, SupervisorError, SupervisorServer


class FakeBackend:
    def __init__(self):
        self.pid = 4242
        self.clients = 0
        self.loaded = False
        self.draining = False
        self.polls = 0
        self.leases = []

    def status(self):
        return {"format": "CORE4-MODEL-SUPERVISOR/1", "running": self.loaded,
                "healthy": self.loaded, "clients": self.clients, "draining": self.draining}

    def warm(self):
        reused = self.loaded
        self.loaded = True
        self.clients += 1
        lease = f"lease-{self.clients}"
        self.leases.append(lease)
        return {"base_url": "http://127.0.0.1:8080/v1", "model_id": "fixture",
                "model_sha256": "a" * 64, "server_pid": self.pid, "owner_id": "owner",
                "gpu_uuids": ["GPU-a", "GPU-b"], "compatibility_key": "b" * 64,
                "slot_id": "slot-a", "service_lease_id": lease, "reused": reused}

    def release(self, service_lease_id=None):
        if service_lease_id is not None:
            self.leases.remove(service_lease_id)
        self.clients = max(0, self.clients - 1)
        return {"released": True, "clients": self.clients}

    def preemption_status(self, service_lease_id=None):
        return {"preempt_requested": False, "draining": self.draining, "clients": self.clients}

    def drain(self):
        self.draining = True
        return {"draining": True, "clients": self.clients}

    def evict(self):
        self.loaded = False
        self.clients = 0
        self.draining = False
        return {"evicted": True, "quiescent": True}

    def poll(self):
        self.polls += 1

    def close(self):
        self.evict()


class SupervisorTests(unittest.TestCase):
    def test_owner_only_protocol_reuses_and_stops(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            backend = FakeBackend()
            server = SupervisorServer(backend, root=root)
            thread = threading.Thread(target=server.serve, daemon=True)
            thread.start()
            deadline = time.monotonic() + 2
            while not server.socket_path.exists() and time.monotonic() < deadline:
                time.sleep(.01)
            client = SupervisorClient(Path(temporary), root=root)
            first = client.request("warm")
            second = client.request("warm")
            self.assertFalse(first["reused"])
            self.assertTrue(second["reused"])
            self.assertEqual(first["server_pid"], second["server_pid"])
            self.assertEqual(first["compatibility_key"], second["compatibility_key"])
            self.assertEqual(os.stat(server.socket_path).st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(root).st_mode & 0o777, 0o700)
            self.assertEqual(client.request("release", service_lease_id=first["service_lease_id"])["clients"], 1)
            self.assertTrue(client.request("drain")["draining"])
            self.assertTrue(client.request("stop")["stopped"])
            thread.join(timeout=2)
            self.assertFalse(thread.is_alive())
            self.assertFalse(server.socket_path.exists())

    def test_status_does_not_spawn_absent_supervisor(self):
        with tempfile.TemporaryDirectory() as temporary:
            client = SupervisorClient(temporary, root=Path(temporary) / "runtime")
            self.assertEqual(client.request("status"), {
                "format": "CORE4-MODEL-SUPERVISOR/1", "running": False, "healthy": False,
            })

    def test_stale_runtime_identity_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            root.mkdir()
            (root / "supervisor.pid").write_text("99999999\n", encoding="ascii")
            (root / "supervisor.sock").write_text("stale", encoding="ascii")
            (root / "supervisor-state.json").write_text("{}", encoding="ascii")
            client = SupervisorClient(temporary, root=root)
            client._recover_stale()
            self.assertFalse((root / "supervisor.pid").exists())
            self.assertFalse((root / "supervisor.sock").exists())
            self.assertFalse((root / "supervisor-state.json").exists())

    def test_busy_owner_socket_is_not_probed_or_restarted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "supervisor.sock").touch()
            (root / "supervisor.pid").write_text(str(os.getpid()) + "\n", encoding="ascii")
            client = SupervisorClient(temporary, root=root)
            with mock.patch.object(client, "_request", side_effect=AssertionError("must not probe busy owner")), \
                 mock.patch("local_worker.supervisor.subprocess.Popen", side_effect=AssertionError("must not restart owner")):
                client.ensure_running()


class _Cache:
    def active(self):
        return {"candidate_id": "fixture", "payload_sha256": "a" * 64}

    def verify(self, candidate_id, sha256, full=False):
        return {"ready": True}

    @contextmanager
    def lease(self, candidate_id, sha256, owner_id):
        yield Path("/models/fixture.gguf")


class _Host:
    def __init__(self, *, islands=2):
        self.bundles = [
            {"resource_ids": ["accelerator:GPU-a", "accelerator:GPU-b"],
             "exclusive_resources": ["interference:nvlink:a"]},
            {"resource_ids": ["accelerator:GPU-c", "accelerator:GPU-d"],
             "exclusive_resources": ["interference:nvlink:b"]},
        ][:islands]
        self.owners = {}
        self.preemptions = set()
        self.serial = 0

    def discover_gpus(self): return []
    def compound_gpu_bundles(self, count): return list(self.bundles)
    def reserve_service(self, **kwargs):
        request = kwargs["resource_request"]
        wanted = set([*request["ids"], *request["exclusive_resources"]])
        if any(wanted & value for value in self.owners.values()):
            return None
        self.serial += 1
        owner = f"owner-{self.serial}"
        self.owners[owner] = wanted
        return {"owner_id": owner, "resource_ids": list(request["ids"])}
    def set_priority(self, owner_id, priority): return owner_id in self.owners
    def heartbeat(self, owner_id, pid=None): return None
    def preempt_requested(self, owner_id): return owner_id in self.preemptions
    def release(self, owner_id): self.owners.pop(owner_id, None)


class _Runtime:
    def __init__(self, islands=2): self.host = _Host(islands=islands)


class _Adapter:
    def describe(self, handle):
        number = int(handle.split("-")[-1])
        return {"base_url": f"http://127.0.0.1:{8079 + number}", "pid": 4200 + number}


class _Service:
    def __init__(self, *, fail_start=0, delay=0.0):
        self.handles = {}
        self.starts = 0
        self.fail_start = fail_start
        self.delay = delay
        self.loading = 0
        self.maximum_loading = 0
        self.lock = threading.Lock()

    def start(self, name, context):
        with self.lock:
            self.loading += 1
            self.maximum_loading = max(self.maximum_loading, self.loading)
            self.starts += 1
            number = self.starts
        try:
            if self.delay: time.sleep(self.delay)
            if number == self.fail_start: raise RuntimeError("fixture start failure")
            handle = f"handle-{number}"
            self.handles[handle] = True
            return handle
        finally:
            with self.lock: self.loading -= 1

    def health(self, name, handle): return {"healthy": self.handles.get(handle, False)}
    def drain(self, name, handle): return {"draining": True}
    def evict(self, name, handle): self.handles[handle] = False; return {"evicted": True}


def _profile(*, maximum=2, ttl=900):
    return {
        "storage": {"cache_root": "/cache", "canonical_root": "/cold"},
        "server": {"binary": "/bin/true", "base_port": 8080, "startup_timeout_seconds": 1,
                   "gpu_layers": 999, "split_mode": "layer"},
        "experiment": {"initial_context": 32768},
        "deployment_policy": {"max_real_workers": maximum, "hot_idle_seconds": ttl},
        "candidates": [{"id": "fixture", "profile": "one-island"}],
    }


class _PoolBackend(ProductionBackend):
    def _healthy(self, slot):
        return bool(self.service.health("llama", slot.handle).get("healthy"))

    def _version(self, binary): return "fixture"


class ServicePoolTests(unittest.TestCase):
    def backend(self, *, islands=2, maximum=2, ttl=900, service=None):
        runtime = _Runtime(islands=islands)
        service = service or _Service()
        backend = _PoolBackend(".", profile=_profile(maximum=maximum, ttl=ttl), cache=_Cache(),
                               runtime=runtime, adapter=_Adapter(), service=service)
        return backend, runtime, service

    def test_two_disjoint_slots_hot_reuse_and_third_rejected(self):
        backend, _, service = self.backend()
        first = backend.warm()
        with self.assertRaisesRegex(SupervisorError, "unknown"):
            backend.release("not-a-lease")
        backend.release(first["service_lease_id"])
        reused = backend.warm()
        self.assertEqual((reused["slot_id"], reused["server_pid"]),
                         (first["slot_id"], first["server_pid"]))
        self.assertTrue(reused["reused"])
        second = backend.warm()
        self.assertNotEqual(reused["slot_id"], second["slot_id"])
        self.assertTrue(set(reused["gpu_uuids"]).isdisjoint(second["gpu_uuids"]))
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable.*retryable"):
            backend.warm()
        self.assertEqual(service.starts, 2)
        backend.close()

    def test_leases_are_exact_and_double_release_is_rejected(self):
        backend, _, _ = self.backend()
        first, second = backend.warm(), backend.warm()
        with self.assertRaisesRegex(SupervisorError, "ambiguous"):
            backend.release()
        backend.release(first["service_lease_id"])
        self.assertEqual(backend.status()["active_leases"], 1)
        with self.assertRaisesRegex(SupervisorError, "unknown or already released"):
            backend.release(first["service_lease_id"])
        self.assertTrue(any(item["slot_id"] == second["slot_id"] and item["leased"]
                            for item in backend.status()["slots"]))
        backend.close()

    def test_slot_ttl_and_selective_then_global_preemption_are_independent(self):
        backend, runtime, _ = self.backend(ttl=0)
        first, second = backend.warm(), backend.warm()
        backend.release(first["service_lease_id"])
        backend.poll()
        self.assertEqual([item["slot_id"] for item in backend.status()["slots"]], [second["slot_id"]])
        replacement = backend.warm()
        runtime.host.preemptions.add(replacement["owner_id"])
        backend.poll()
        remaining = backend.status()["slots"]
        self.assertEqual([item["slot_id"] for item in remaining], [second["slot_id"]])
        runtime.host.preemptions.add(second["owner_id"])
        backend.poll()
        self.assertFalse(backend.status()["running"])

    def test_cold_starts_serialize_and_second_failure_preserves_first(self):
        service = _Service(delay=.03)
        backend, _, _ = self.backend(service=service)
        results = []
        threads = [threading.Thread(target=lambda: results.append(backend.warm())) for _ in range(2)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual((len(results), service.maximum_loading), (2, 1))
        backend.close()

        failing = _Service(fail_start=2)
        backend, _, _ = self.backend(service=failing)
        first = backend.warm()
        with self.assertRaisesRegex(RuntimeError, "fixture start failure"):
            backend.warm()
        self.assertEqual(backend.status()["slots"][0]["server_pid"], first["server_pid"])
        backend.release(first["service_lease_id"])
        self.assertTrue(backend.warm()["reused"])
        backend.close()

    def test_single_island_fallback_remains_unchanged(self):
        backend, _, _ = self.backend(islands=1)
        first = backend.warm()
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable"):
            backend.warm()
        backend.release(first["service_lease_id"])
        self.assertTrue(backend.warm()["reused"])
        backend.close()


if __name__ == "__main__":
    unittest.main()
