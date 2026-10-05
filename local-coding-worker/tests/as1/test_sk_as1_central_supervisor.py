"""Actual Unix RPC with CPU model fixtures; no GPU or inference execution."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_supervisor import _Adapter, _Cache, _Host, _PoolBackend, _Service, _profile
from local_worker.supervisor import (RPC_FRAME_BYTES, SupervisorClient, SupervisorError,
                                    SupervisorServer, _check_peer_uid, main)
from local_worker.residency import process_identity


class CentralBackend(_PoolBackend):
    def _version(self, binary, deadline_epoch=None):
        return "fixture"


class CentralSupervisorTests(unittest.TestCase):
    def setUp(self):
        context = {"fixture": "canonical-runtime"}
        identity = SimpleNamespace(public=lambda: context)
        binding = patch("local_worker.supervisor.bind_canonical_runtime", return_value=(identity, context))
        validation = patch("local_worker.supervisor.validate_canonical_runtime")
        binding.start()
        validation.start()
        self.addCleanup(binding.stop)
        self.addCleanup(validation.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.state = Path(self.directory.name)
        self.service = _Service()
        self.host = _Host()
        profile = _profile(maximum=2)
        profile["deployment_policy"]["allowed_gpu_uuids"] = ["GPU-a", "GPU-b", "GPU-c", "GPU-d"]
        self.backend = CentralBackend(self.state, service_state_root=self.state, profile=profile,
            cache=_Cache(), runtime=SimpleNamespace(host=self.host), service=self.service,
            adapter=_Adapter(), topology_classifier=lambda: SimpleNamespace(mode="normal", status="available"))
        self.server = SupervisorServer(self.backend, root=self.state / "runtime", observer_only=True)
        self.failures = []
        def serve():
            try:
                self.server.serve()
            except Exception as error:
                self.failures.append(error)
        self.thread = threading.Thread(target=serve, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)
        deadline = time.monotonic() + 3
        while not self.server.socket_path.exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue(self.server.socket_path.exists())
        self.client = self.new_client()

    def new_client(self):
        return SupervisorClient(self.state, root=self.state / "runtime")

    def shutdown(self):
        self.server.stop_accepting()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.failures, [])

    def turn(self, session_id=None, text="fixture", deadline_epoch=None):
        request = {"format": "PC-LOCAL-INVESTIGATOR-TURN/2",
            "messages": [{"role": "user", "content": text}], "max_tokens": 32,
            "timeout_seconds": 1, "compute_profile": "narrow", "parallelism": "layer"}
        if session_id is not None:
            request["session_id"] = session_id
        if deadline_epoch is not None:
            request["deadline_epoch"] = deadline_epoch
        return request

    def test_status_identity_policy_and_client_close_preserve_warm_pool(self):
        sessions = self.client.open_observer_sessions(2, compute_profile="narrow", parallelism="layer")
        first = self.client.observer_status(deadline_epoch=time.time() + 2)
        import local_worker.supervisor as supervisor
        self.assertEqual(first["observer_contract"], "PC-OBSERVER-SUPERVISOR/1")
        self.assertTrue(first["observer_only"])
        self.assertEqual(first["source_sha256"], hashlib.sha256(Path(supervisor.__file__).read_bytes()).hexdigest())
        self.assertEqual(first["supervisor_pid"], os.getpid())
        self.assertEqual(first["supervisor_process_start"], process_identity(os.getpid())["process_start"])
        self.assertEqual(first["service_state_root"], str(self.state))
        self.assertEqual(first["runtime_root"], str(self.state / "runtime"))
        self.assertEqual(first["allowed_gpu_uuids"], ["GPU-a", "GPU-b", "GPU-c", "GPU-d"])
        self.assertEqual(first["idle_ttl_seconds"], 900)
        self.assertEqual({slot["service_lease_id"] for slot in first["slots"]}, set(sessions["session_ids"]))
        self.assertTrue(all(slot["server_pid"] and slot["owner_id"] for slot in first["slots"]))
        self.client.close()
        second = self.new_client().observer_status()
        self.assertEqual(first["slots"], second["slots"])
        for session in sessions["session_ids"]:
            self.assertTrue(self.client.close_observer_session(session)["released"])
        idle = self.client.observer_status()
        self.assertEqual(idle["active_leases"], 0)
        self.assertTrue(idle["running"])
        self.assertEqual({slot["server_pid"] for slot in first["slots"]},
                         {slot["server_pid"] for slot in idle["slots"]})
        self.client.open_observer_sessions(1)
        self.assertEqual(self.service.starts, 2)

    def test_two_sessions_and_clients_overlap_third_call_busy_status_responsive(self):
        sessions = self.client.open_observer_sessions(2)["session_ids"]
        entered = threading.Barrier(3)
        resume = threading.Event()
        self.addCleanup(resume.set)
        original_run = self.service.run
        def blocked_run(name, handle, request):
            entered.wait(timeout=2)
            if not resume.wait(timeout=3):
                raise RuntimeError("fixture release timed out")
            result = original_run(name, handle, request)
            result["text"] = request["messages"][-1]["content"]
            return result
        self.service.run = blocked_run
        with ThreadPoolExecutor(max_workers=2) as workers:
            first = workers.submit(self.new_client().run_observer_turn, self.turn(sessions[0], "first"))
            second = workers.submit(self.new_client().run_observer_turn, self.turn(sessions[1], "second"))
            entered.wait(timeout=2)
            before = time.monotonic()
            status = self.client.observer_status(deadline_epoch=time.time() + .5)
            self.assertLess(time.monotonic() - before, .5)
            self.assertEqual(status["active_leases"], 2)
            busy = self.client.run_observer_turn(self.turn())
            self.assertEqual(busy["reason"], "observer_provider_busy")
            self.assertEqual(self.client.analyze_observer_packet({})["reason"], "observer_provider_busy")
            resume.set()
            self.assertEqual(first.result(timeout=2)["text"], "first")
            self.assertEqual(second.result(timeout=2)["text"], "second")
        self.assertEqual(len(self.service.requests), 2)
        self.assertEqual(len({request[1] for request in self.service.requests}), 2)

    def test_status_responds_while_cold_start_lifecycle_lock_is_held(self):
        held, release = threading.Event(), threading.Event()
        def lifecycle():
            with self.backend._pool_lock:
                held.set()
                release.wait(timeout=2)
        worker = threading.Thread(target=lifecycle)
        worker.start()
        self.assertTrue(held.wait(timeout=1))
        try:
            self.assertEqual(self.client.observer_status(deadline_epoch=time.time() + .5)["capacity"], 2)
        finally:
            release.set()
            worker.join(timeout=1)

    def test_absent_owner_never_autostarts_or_constructs_backend(self):
        absent = SupervisorClient(self.state, root=self.state / "absent")
        with patch.object(absent, "ensure_running", side_effect=AssertionError("autostart")), \
             patch("local_worker.supervisor.subprocess.Popen", side_effect=AssertionError("spawn")):
            for call in (absent.observer_status, lambda: absent.run_observer_turn(self.turn()),
                         lambda: absent.analyze_observer_packet({}), lambda: absent.open_observer_sessions(1),
                         lambda: absent.close_observer_session("session")):
                with self.assertRaisesRegex(SupervisorError, "central_supervisor_unavailable"):
                    call()
            absent.close()

    def raw(self, data):
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.settimeout(2)
            connection.connect(str(self.server.socket_path))
            connection.sendall(data)
            connection.shutdown(socket.SHUT_WR)
            result = b""
            while b"\n" not in result:
                result += connection.recv(4096)
            return json.loads(result)

    def test_malformed_and_oversized_requests_and_responses_are_explicit(self):
        for data in (b"[]\n", b"not-json\n", b'{"operation":NaN}\n', b'{}', b'{}\n{}\n'):
            with self.subTest(data=data):
                self.assertFalse(self.raw(data)["ok"])
        self.assertEqual(self.raw(b"x" * (RPC_FRAME_BYTES + 1))["error"], "supervisor_frame_too_large")
        with self.assertRaisesRegex(SupervisorError, "frame_too_large"):
            self.client.run_observer_turn({"text": "x" * RPC_FRAME_BYTES})
        self.backend.run_observer_turn = lambda request: {"text": "x" * RPC_FRAME_BYTES}
        with self.assertRaisesRegex(SupervisorError, "frame_too_large"):
            self.client.run_observer_turn(self.turn())

    def test_peer_uid_socket_permissions_symlink_and_owner_pid_are_checked(self):
        peer = Mock()
        peer.getsockopt.return_value = struct.pack("3i", os.getpid(), os.getuid() + 1, os.getgid())
        with self.assertRaisesRegex(SupervisorError, "peer_uid_mismatch"):
            _check_peer_uid(peer)
        self.server.socket_path.chmod(0o666)
        with self.assertRaisesRegex(SupervisorError, "private_path_invalid"):
            self.client.observer_status()
        self.server.socket_path.chmod(0o600)
        alias = self.state / "alias"
        alias.symlink_to(self.server.root)
        with self.assertRaisesRegex(SupervisorError, "private_path_invalid"):
            SupervisorClient(self.state, root=alias).observer_status()
        original = self.server._observer_status
        with patch.object(self.server, "_observer_status", side_effect=lambda: {**original(), "supervisor_pid": 1}):
            with self.assertRaisesRegex(SupervisorError, "process_identity_mismatch"):
                self.client.observer_status()

    def test_deadlines_invalid_and_transport_timeout_do_not_evict_pool(self):
        sessions = self.client.open_observer_sessions(1)["session_ids"]
        for deadline in (True, float("nan"), time.time() - 1):
            with self.subTest(deadline=deadline):
                with self.assertRaises((ValueError, TimeoutError, SupervisorError)):
                    self.client.run_observer_turn(self.turn(sessions[0], deadline_epoch=deadline))
        original = self.backend.run_observer_turn
        entered, resume = threading.Event(), threading.Event()
        self.addCleanup(resume.set)
        def delayed(request):
            entered.set()
            resume.wait(timeout=2)
            return original({**request, "deadline_epoch": time.time() + 1})
        self.backend.run_observer_turn = delayed
        with self.assertRaisesRegex(SupervisorError, "central_supervisor_timeout"):
            self.client.run_observer_turn(self.turn(sessions[0], deadline_epoch=time.time() + .05))
        self.assertTrue(entered.is_set())
        self.assertEqual(self.client.observer_status()["active_leases"], 1)
        resume.set()

    def test_observer_only_denies_maintenance_and_stop_is_verified(self):
        for operation in ("status", "admit", "warm", "release", "evict", "drain"):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(SupervisorError, "maintenance_disabled"):
                    self.client._request(operation)
        with patch.object(self.backend, "evict", return_value={"quiescent": False}):
            with self.assertRaisesRegex(SupervisorError, "stop_not_quiescent"):
                self.client.request("stop")
        self.assertFalse(self.server.stopping)
        self.assertTrue(self.client.request("stop")["stopped"])
        self.thread.join(timeout=2)

    def test_operator_cli_roots_and_gpu_policy_bindings(self):
        args = ["--serve", "--repo-root", str(self.state), "--service-state-root", str(self.state),
                "--runtime-root", str(self.state / "runtime"), "--observer-only", "--allowed-gpu-uuid", "GPU-a"]
        with patch.dict(os.environ, {"PROJECT_CONTROL_OBSERVER_ANALYSIS_STATE_DIR": str(self.state),
                                    "PROJECT_CONTROL_OBSERVER_GPU_UUIDS": '["GPU-a","GPU-b"]'}, clear=False), \
             patch("local_worker.supervisor.ProductionBackend") as backend, \
             patch("local_worker.supervisor.SupervisorServer") as server:
            server.return_value.serve.return_value = 0
            self.assertEqual(main(args), 0)
            self.assertEqual(backend.call_args.kwargs["service_state_root"], str(self.state))
            self.assertEqual(backend.call_args.kwargs["profile"]["deployment_policy"]["allowed_gpu_uuids"], ["GPU-a"])
            self.assertTrue(server.call_args.kwargs["observer_only"])
            with self.assertRaisesRegex(SupervisorError, "gpu_allowlist_mismatch"):
                main(args[:-1] + ["GPU-foreign"])
            with self.assertRaisesRegex(SupervisorError, "runtime_root_mismatch"):
                main([*args[:6], "/foreign", *args[7:]])

    def test_connection_bound_and_runtime_identity_rejection(self):
        with patch.object(self.server._connections, "acquire", return_value=False):
            self.assertEqual(self.raw(b'{"operation":"observer-status"}\n')["error"],
                             "supervisor_connections_busy")
        original = self.server.runtime_context
        self.server.runtime_context = {"foreign": True}
        try:
            with self.assertRaisesRegex(SupervisorError, "runtime_identity_mismatch"):
                self.client.observer_status()
        finally:
            self.server.runtime_context = original

    def test_owner_binding_between_status_and_operation_and_deadline_cap(self):
        self.client.observer_status()
        self.client._observer_owner = (os.getpid(), "wrong-start")
        with self.assertRaisesRegex(SupervisorError, "process_identity_mismatch"):
            self.client.open_observer_sessions(1)
        self.assertEqual(self.service.starts, 0)
        self.client.observer_status()
        with patch.object(self.backend, "run_observer_turn", return_value={"status": "available"}) as run:
            self.client.run_observer_turn(self.turn(deadline_epoch=time.time() + 9000))
            self.assertLessEqual(run.call_args.args[0]["deadline_epoch"] - time.time(), 300)

    def test_signal_stop_verifies_cleanup_of_only_fake_owned_models(self):
        self.client.open_observer_sessions(2)
        self.assertEqual(len(self.host.owners), 2)
        self.server.stop_accepting()
        self.thread.join(timeout=2)
        self.assertFalse(self.thread.is_alive())
        self.assertEqual(self.host.owners, {})
        self.assertEqual(self.backend._slots, {})
        self.assertFalse(self.server.socket_path.exists())
        self.assertEqual(self.failures, [])


if __name__ == "__main__":
    unittest.main()
