from __future__ import annotations

import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

CUDA_ROOT = Path(__file__).resolve().parents[1]
TODO_ROOT = CUDA_ROOT.parent / "todo-orchestrator"
for item in (CUDA_ROOT / "scripts", TODO_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import cuda_controller as controller
from cuda_quiescence import prove_quiescence
from todo_orchestrator.background.host import HostCoordinator


class Core4CudaInterlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {"TODO_BACKGROUND_HOST_RUNTIME_DIR": self.temporary.name})
        self.environment.start()
        self.host = HostCoordinator()
        self.host.upsert_resources([
            {"id": "accelerator:probe-0", "kind": "accelerator", "tags": {"nvlink_domain": "runtime-domain"}},
            {"id": "accelerator:probe-1", "kind": "accelerator", "tags": {"nvlink_domain": "runtime-domain"}},
        ])

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def test_controller_declares_clean_foreground_priority(self) -> None:
        source = inspect.getsource(controller.foreground_run)
        self.assertIn('priority_class="clean_cuda_foreground"', source)

    def test_clean_foreground_waits_for_service_release_then_quiescence_can_pass(self) -> None:
        service = self.host.reserve_service(
            project_root=self.temporary.name, service_id="local", pid=os.getpid(),
            request={"count": 2, "isolate_nvlink_domain": True},
            priority_class="active_local_delegation",
        )
        foreground, resources = self.host.begin_foreground(
            project_root=self.temporary.name,
            request={"count": 2, "isolate_nvlink_domain": True}, pid=os.getpid(),
            priority_class="clean_cuda_foreground",
        )
        self.assertTrue(self.host.preempt_requested(service[0]))
        self.assertFalse(self.host.activate_foreground(foreground, resources))
        self.host.release(service[0])
        self.assertTrue(self.host.activate_foreground(foreground, resources))
        proof = prove_quiescence(
            [item.removeprefix("accelerator:") for item in resources if item.startswith("accelerator:")],
            lambda uuids: {"idle": True, "busy": [], "foreign_processes": [], "uuids": uuids},
            consecutive_idle_samples=2, interval_seconds=0.01,
        )
        self.assertTrue(proof["uncontaminated"])
        self.assertEqual(proof["device_uuids"], ["probe-0", "probe-1"])


if __name__ == "__main__":
    unittest.main()
