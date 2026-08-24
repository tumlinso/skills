from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.supervisor import SupervisorClient, SupervisorServer


class FakeBackend:
    def __init__(self):
        self.pid = 4242
        self.clients = 0
        self.loaded = False
        self.draining = False
        self.polls = 0

    def status(self):
        return {"format": "CORE4-MODEL-SUPERVISOR/1", "running": self.loaded,
                "healthy": self.loaded, "clients": self.clients, "draining": self.draining}

    def warm(self):
        reused = self.loaded
        self.loaded = True
        self.clients += 1
        return {"base_url": "http://127.0.0.1:8080/v1", "model_id": "fixture",
                "model_sha256": "a" * 64, "server_pid": self.pid, "owner_id": "owner",
                "gpu_uuids": ["GPU-a", "GPU-b"], "compatibility_key": "b" * 64,
                "reused": reused}

    def release(self):
        self.clients = max(0, self.clients - 1)
        return {"released": True, "clients": self.clients}

    def preemption_status(self):
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
            self.assertEqual(client.request("release")["clients"], 1)
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


if __name__ == "__main__":
    unittest.main()
