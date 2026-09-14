from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.supervisor import AdapterError, ProductionBackend, SupervisorClient, SupervisorError, SupervisorServer, runtime_root


class FakeBackend:
    def __init__(self):
        self.pid = 4242
        self.clients = 0
        self.loaded = False
        self.draining = False
        self.polls = 0
        self.leases = []
        self.admissions = []

    def status(self):
        return {"format": "CORE4-MODEL-SUPERVISOR/1", "running": self.loaded,
                "healthy": self.loaded, "clients": self.clients, "draining": self.draining}

    def admit(self):
        admission = f"admission-{len(self.admissions) + 1}"
        self.admissions.append(admission)
        return {"status": "admitted", "admission_id": admission}

    def cancel_admission(self, admission_id):
        self.admissions.remove(admission_id)
        return {"cancelled": True, "admission_id": admission_id}

    def warm(self, admission_id=None):
        if admission_id is not None:
            self.admissions.remove(admission_id)
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
        self.admissions.clear()
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

    def test_owner_protocol_admission_is_explicit_and_cancellable(self):
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
            admitted = client.request("admit")
            self.assertEqual(backend.clients, 0)
            self.assertEqual(client.request("cancel-admission", admission_id=admitted["admission_id"])["cancelled"], True)
            client.request("stop")
            thread.join(timeout=2)

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

    def test_live_owner_is_probed_and_runtime_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "supervisor.sock").touch()
            (root / "supervisor.pid").write_text(str(os.getpid()) + "\n", encoding="ascii")
            client = SupervisorClient(temporary, root=root)
            with mock.patch.object(client, "_request", return_value={"running": True}), \
                 mock.patch("local_worker.supervisor.subprocess.Popen", side_effect=AssertionError("must not restart owner")):
                with self.assertRaisesRegex(SupervisorError, "runtime_identity_mismatch"):
                    client.ensure_running()

    def test_authority_database_path_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            client = SupervisorClient(temporary, root=Path(temporary) / "runtime")
            observed = dict(client.runtime_context)
            observed["db_path"] = "/different/state.sqlite3"
            with self.assertRaisesRegex(SupervisorError, "runtime_identity_mismatch"):
                client._validate_status({"runtime_identity": observed})


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
        self.discoveries = 0
        self.priority_changes = 0

    def discover_gpus(self): self.discoveries += 1; return []
    def compound_gpu_bundles(self, count):
        if count == 4 and len(self.bundles) == 2:
            return [{"resource_ids": [item for bundle in self.bundles for item in bundle["resource_ids"]],
                     "exclusive_resources": [item for bundle in self.bundles for item in bundle["exclusive_resources"]]}]
        return list(self.bundles)
    def reserve_service(self, **kwargs):
        request = kwargs["resource_request"]
        wanted = set([*request["ids"], *request["exclusive_resources"]])
        if any(wanted & value for value in self.owners.values()):
            return None
        self.serial += 1
        owner = f"owner-{self.serial}"
        self.owners[owner] = wanted
        return {"owner_id": owner, "resource_ids": list(request["ids"])}
    def set_priority(self, owner_id, priority):
        self.priority_changes += 1
        return owner_id in self.owners
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
    def __init__(self, *, fail_start=0, delay=0.0, fail_run=False):
        self.handles = {}
        self.starts = 0
        self.fail_start = fail_start
        self.delay = delay
        self.loading = 0
        self.maximum_loading = 0
        self.lock = threading.Lock()
        self.fail_run = fail_run
        self.requests = []

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
    def run(self, name, handle, request):
        self.requests.append((name, handle, request))
        if self.fail_run:
            raise AdapterError("fixture run failure")
        return {"text": '{"action":"answer"}', "usage": {"completion_tokens": 7}}
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
    def test_backend_creates_its_private_runtime_namespace(self):
        with tempfile.TemporaryDirectory() as temporary:
            namespace = Path(temporary) / "app" / "observer-analysis"
            _PoolBackend("/read-only-observed-repository", service_state_root=namespace,
                         profile=_profile(maximum=1), cache=_Cache(),
                         runtime=_Runtime(), adapter=_Adapter(), service=_Service(),
                         topology_classifier=lambda: SimpleNamespace(mode="x_mode", status="available"))
            self.assertTrue(namespace.is_dir())
            self.assertEqual(namespace.stat().st_mode & 0o777, 0o700)

    def test_observer_service_state_owns_logs_and_model_leases(self):
        with tempfile.TemporaryDirectory() as temporary:
            namespace = Path(temporary) / "observer-service"
            backend = _PoolBackend("/read-only-observed-repository", service_state_root=namespace,
                                   profile=_profile(maximum=1), cache=_Cache(), runtime=_Runtime(),
                                   adapter=_Adapter(), service=_Service(),
                                   topology_classifier=lambda: SimpleNamespace(mode="x_mode", status="available"))
            self.assertEqual(backend._state_root(), namespace / "state")
            self.assertEqual(backend.service_state_root, namespace)
            self.assertEqual(runtime_root(namespace), namespace / "runtime")

    def backend(self, *, islands=2, maximum=2, ttl=900, service=None):
        runtime = _Runtime(islands=islands)
        service = service or _Service()
        topology = {"value": SimpleNamespace(mode="normal", status="available")}
        backend = _PoolBackend(".", profile=_profile(maximum=maximum, ttl=ttl), cache=_Cache(),
                               runtime=runtime, adapter=_Adapter(), service=service,
                               topology_classifier=lambda: topology["value"])
        backend.test_topology = topology
        return backend, runtime, service

    def test_x_mode_admits_idle_service_with_existing_reservation_safety(self):
        backend, runtime, service = self.backend(maximum=1)
        endpoint = backend.warm()
        backend.release(endpoint["service_lease_id"])
        backend.test_topology["value"] = SimpleNamespace(mode="x_mode", status="available")
        admission = backend.admit()
        self.assertEqual(admission["status"], "admitted")
        self.assertEqual(backend.status()["slots"][0]["state"], "idle")
        backend.cancel_admission(admission["admission_id"])
        backend.close()

    def test_topology_change_does_not_disturb_active_work_and_respects_capacity(self):
        backend, runtime, service = self.backend(maximum=1)
        endpoint = backend.warm()
        owners = dict(runtime.host.owners)
        backend.test_topology["value"] = SimpleNamespace(mode="x_mode", status="available")
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable"):
            backend.admit()
        self.assertEqual(dict(runtime.host.owners), owners)
        self.assertTrue(service.handles)
        slot = backend.status()["slots"][0]
        self.assertEqual((slot["state"], slot["leased"]), ("active", True))
        backend.release(endpoint["service_lease_id"])
        backend.close()

    def test_existing_admission_survives_change_to_x_mode(self):
        backend, _, service = self.backend()
        admission = backend.admit()
        backend.test_topology["value"] = SimpleNamespace(mode="x_mode", status="available")
        endpoint = backend.warm(admission["admission_id"])
        self.assertEqual((endpoint["reused"], service.starts), (False, 1))
        backend.release(endpoint["service_lease_id"])
        backend.close()

    def test_direct_warm_reuses_x_mode_slot_with_reservation_checks(self):
        backend, runtime, service = self.backend()
        endpoint = backend.warm()
        backend.release(endpoint["service_lease_id"])
        backend.test_topology["value"] = SimpleNamespace(mode="x_mode", status="available")
        reused = backend.warm()
        self.assertTrue(reused["reused"])
        backend.release(reused["service_lease_id"])
        backend.close()

        backend, runtime, service = self.backend()
        backend.test_topology["value"] = SimpleNamespace(mode="unknown", status="unsupported")
        with self.assertRaisesRegex(SupervisorError, "HOST_TOPOLOGY_UNSUPPORTED"):
            backend.warm()
        self.assertEqual((service.starts, runtime.host.discoveries, runtime.host.owners), (0, 0, {}))
        backend.close()

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

    def test_two_concurrent_services_reserve_the_two_disjoint_nvlink_pairs(self):
        backend, _, _ = self.backend()
        first, second = backend.warm(), backend.warm()
        self.assertEqual(
            {frozenset(first["gpu_uuids"]), frozenset(second["gpu_uuids"])},
            {frozenset({"GPU-a", "GPU-b"}), frozenset({"GPU-c", "GPU-d"})},
        )
        backend.close()

    def test_compute_profiles_use_compatible_two_or_four_gpu_slots(self):
        backend, _, service = self.backend()
        default = backend.warm(compute_profile="default")
        self.assertEqual((default["compute_profile"], len(default["gpu_uuids"])), ("default", 2))
        backend.release(default["service_lease_id"])
        reused = backend.warm(compute_profile="default")
        self.assertTrue(reused["reused"])
        backend.release(reused["service_lease_id"])
        wide = backend.warm(compute_profile="wide")
        self.assertEqual((wide["compute_profile"], len(wide["gpu_uuids"])), ("wide", 4))
        self.assertFalse(wide["reused"])
        self.assertEqual(service.starts, 2)
        backend.close()

    def test_wide_never_evicts_an_active_incompatible_slot(self):
        backend, runtime, service = self.backend()
        active = backend.warm(compute_profile="default")
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable"):
            backend.admit("wide")
        self.assertEqual(service.starts, 1)
        self.assertEqual(backend.status()["slots"][0]["state"], "active")
        self.assertIn(active["owner_id"], runtime.host.owners)
        backend.close()

    def test_observer_turn_reports_wide_profile_metadata(self):
        backend, _, service = self.backend()
        result = backend.run_observer_turn({"format": "PC-LOCAL-INVESTIGATOR-TURN/2", "messages": [
            {"role": "system", "content": "investigate"}, {"role": "user", "content": "question"},
        ], "max_tokens": 128, "timeout_seconds": 10, "compute_profile": "wide"})
        self.assertEqual((result["status"], result["model_id"], result["compute_profile"]),
                         ("available", "fixture", "wide"))
        self.assertEqual(len(backend.status()["slots"][0]["gpu_uuids"]), 4)
        backend.close()

    def test_admission_reserves_capacity_before_model_or_service_start(self):
        backend, runtime, service = self.backend()
        first = backend.admit()
        second = backend.admit()
        self.assertEqual((service.starts, backend.status()["active_admissions"]), (0, 2))
        self.assertEqual(len(runtime.host.owners), 2)
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable"):
            backend.admit()
        with self.assertRaisesRegex(SupervisorError, "resource_unavailable"):
            backend.warm()
        endpoint = backend.warm(first["admission_id"])
        self.assertEqual((service.starts, backend.status()["active_admissions"]), (1, 1))
        backend.release(endpoint["service_lease_id"])
        backend.cancel_admission(second["admission_id"])
        self.assertEqual(backend.status()["active_admissions"], 0)
        backend.close()

    def test_expired_admission_is_swept_without_starting_a_service(self):
        backend, _, service = self.backend()
        backend.admission_ttl = 0
        admission = backend.admit()
        backend.poll()
        self.assertEqual((backend.status()["active_admissions"], service.starts), (0, 0))
        with self.assertRaisesRegex(SupervisorError, "unknown, expired"):
            backend.warm(admission["admission_id"])
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

    def test_observer_turn_rejects_non_text_protocol_fields_before_admission(self):
        backend, runtime, service = self.backend()
        request = {"format": "PC-LOCAL-INVESTIGATOR-TURN/2", "messages": [
            {"role": "system", "content": "investigate"},
        ], "max_tokens": 128, "timeout_seconds": 30, "tools": []}
        result = backend.run_observer_turn(request)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "investigator_turn_invalid_request")
        self.assertEqual((service.starts, runtime.host.owners), (0, {}))
        backend.close()

    def test_observer_turn_forwards_only_text_messages_and_releases_lease(self):
        backend, _, service = self.backend()
        request = {"format": "PC-LOCAL-INVESTIGATOR-TURN/2", "messages": [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "evidence E-1"},
            {"role": "assistant", "content": "{\"action\":\"search_source\"}"},
        ], "max_tokens": 256, "timeout_seconds": 20}
        result = backend.run_observer_turn(request)
        self.assertEqual(result, {"status": "available", "authoritative": False,
                                  "text": '{"action":"answer"}',
                                  "usage": {"completion_tokens": 7}, "provider": "llama-server",
                                  "warm_model_reused": False, "model_id": "fixture",
                                  "compute_profile": "default", "compatibility_key": result["compatibility_key"]})
        self.assertEqual(service.requests[0][2], {"messages": request["messages"],
                                                   "max_tokens": 256, "timeout_seconds": 20.0})
        self.assertEqual(backend.status()["active_leases"], 0)
        backend.close()

    def test_observer_turn_cancels_admission_and_releases_on_errors(self):
        backend, runtime, service = self.backend(service=_Service(fail_run=True))
        request = {"format": "PC-LOCAL-INVESTIGATOR-TURN/2", "messages": [
            {"role": "user", "content": "question"},
        ], "max_tokens": 128, "timeout_seconds": 15}
        failed_run = backend.run_observer_turn(request)
        self.assertEqual((failed_run["status"], backend.status()["active_leases"]), ("unavailable", 0))
        self.assertEqual(backend.status()["active_admissions"], 0)
        owners_before_warm_failure = dict(runtime.host.owners)
        with mock.patch.object(backend, "warm", side_effect=SupervisorError("fixture warm failure")):
            failed_warm = backend.run_observer_turn(request)
        self.assertEqual(failed_warm["status"], "unavailable")
        self.assertEqual(backend.status()["active_admissions"], 0)
        self.assertEqual(runtime.host.owners, owners_before_warm_failure)
        backend.close()

    def test_observer_turn_busy_returns_unavailable_without_admission(self):
        backend, runtime, service = self.backend()
        backend._analysis_lock.acquire()
        try:
            result = backend.run_observer_turn({"format": "PC-LOCAL-INVESTIGATOR-TURN/2", "messages": [
                {"role": "user", "content": "question"},
            ], "max_tokens": 64, "timeout_seconds": 10})
        finally:
            backend._analysis_lock.release()
        self.assertEqual((result["status"], result["reason"]), ("unavailable", "observer_provider_busy"))
        self.assertEqual((service.starts, runtime.host.owners), (0, {}))
        backend.close()


if __name__ == "__main__":
    unittest.main()
