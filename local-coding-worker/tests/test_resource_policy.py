from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
TODO = SKILL.parent / "todo-orchestrator"
for item in (SKILL, TODO):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from local_worker.service import AdapterError, AdapterService
from todo_orchestrator.background.host import HostCoordinator


class FakeAdapter:
    def __init__(self, during_run=None):
        self.calls: list[str] = []
        self.during_run = during_run

    def inspect(self): return {"available": True}
    def start(self, context): self.calls.append("start"); return "handle"
    def health(self, handle): return {"healthy": True}
    def run(self, handle, request):
        self.calls.append("run")
        if self.during_run:
            self.during_run()
        return {"status": "succeeded", "text": "bounded"}
    def cancel(self, handle, request_id=None): return {"canceled": True}
    def drain(self, handle): self.calls.append("drain"); return {"draining": True}
    def evict(self, handle): self.calls.append("evict"); return {"evicted": True}
    def usage(self, handle): return {"runs": self.calls.count("run")}


class LocalWorkerResourcePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {"TODO_BACKGROUND_HOST_RUNTIME_DIR": self.temporary.name})
        self.environment.start()
        self.host = HostCoordinator()
        self.host.upsert_resources([{"id": "accelerator:dynamic", "kind": "accelerator", "tags": {}}])
        self.project = Path(self.temporary.name) / "project"

    def tearDown(self) -> None:
        self.environment.stop()
        self.temporary.cleanup()

    def owner(self):
        connection = self.host.connect(readonly=True)
        try:
            row = connection.execute("SELECT id FROM host_owners WHERE owner_kind='service' ORDER BY acquired_at DESC LIMIT 1").fetchone()
            return self.host.owner(str(row[0])) if row else None
        finally:
            connection.close()

    def test_opt_in_service_is_active_only_during_run_then_resident(self) -> None:
        seen: list[str] = []
        adapter = FakeAdapter(lambda: seen.append(str(self.owner()["priority_class"])))
        service = AdapterService(resource_coordinator=self.host, project_root=self.project, resource_poll_seconds=0.01)
        service.register("fake", adapter)
        handle = service.start("fake", {"resource_request": {"ids": ["accelerator:dynamic"]}})
        self.assertEqual(self.owner()["priority_class"], "idle_model_residency")
        self.assertEqual(service.run("fake", handle, {})["status"], "succeeded")
        self.assertEqual(seen, ["active_local_delegation"])
        self.assertEqual(self.owner()["priority_class"], "idle_model_residency")
        service.evict("fake", handle)

    def test_clean_foreground_signal_drains_evicts_and_returns_needs_codex(self) -> None:
        adapter = FakeAdapter()
        service = AdapterService(resource_coordinator=self.host, project_root=self.project)
        service.register("fake", adapter)
        handle = service.start("fake", {"resource_request": {"ids": ["accelerator:dynamic"]}})
        foreground, resources = self.host.begin_foreground(
            project_root=self.project, request={"ids": ["accelerator:dynamic"]}, pid=os.getpid(),
            priority_class="clean_cuda_foreground",
        )
        deadline = time.monotonic() + 1
        while "evict" not in adapter.calls and time.monotonic() < deadline:
            time.sleep(0.01)
        result = service.run("fake", handle, {})
        self.assertEqual(result["outcome"], "NEEDS_CODEX")
        self.assertEqual(adapter.calls, ["start", "drain", "evict"])
        self.assertTrue(self.host.activate_foreground(foreground, resources))

    def test_resource_start_never_starts_adapter_while_background_is_owned(self) -> None:
        background = self.host.reserve_background(
            project_root=self.project, job_id="campaign", attempt_id="attempt",
            request={"ids": ["accelerator:dynamic"]}, pid=os.getpid(),
        )
        adapter = FakeAdapter()
        service = AdapterService(resource_coordinator=self.host, project_root=self.project)
        service.register("fake", adapter)
        with self.assertRaisesRegex(AdapterError, "pending lower-priority owner drain"):
            service.start("fake", {"resource_request": {"ids": ["accelerator:dynamic"]}})
        self.assertEqual(adapter.calls, [])
        self.assertTrue(self.host.preempt_requested(background[0]))

    def test_existing_uncoordinated_adapter_calls_are_unchanged(self) -> None:
        adapter = FakeAdapter()
        service = AdapterService()
        service.register("fake", adapter)
        handle = service.start("fake", {})
        self.assertEqual(service.run("fake", handle, {})["text"], "bounded")
        self.assertTrue(service.evict("fake", handle)["evicted"])


if __name__ == "__main__":
    unittest.main()
