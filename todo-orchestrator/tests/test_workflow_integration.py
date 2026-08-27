from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.models import TodoError
from todo_orchestrator.workflow.capabilities import WorkflowCapabilityLocator
from todo_orchestrator.workflow.protocol import WorkflowProtocol
from todo_orchestrator.workflow.protocol import _validate_action
from todo_orchestrator.workflow.service import WorkflowKernel


class FakeLocalWorker:
    def delegate(self, **kwargs):
        return {"status": "running"}

    def collect(self, **kwargs):
        return {
            "status": "candidate_available",
            "kind": "source_finding",
            "result": {"summary": "bounded finding"},
            "artifacts": [],
        }


class WorkflowKernelIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.repo = V2Repo()
        (self.repo.root / "src" / "a").mkdir(parents=True)
        (self.repo.root / "src" / "a" / "unit.py").write_text("value = 1\n", encoding="utf-8")
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        self.locator_temp = tempfile.TemporaryDirectory()
        self.locator = WorkflowCapabilityLocator(Path(self.locator_temp.name))
        self.kernel = WorkflowKernel(locator=self.locator, local_worker_adapter=FakeLocalWorker())
        self.protocol = WorkflowProtocol(self.kernel, self.locator)

    def tearDown(self):
        self.repo.close()
        self.locator_temp.cleanup()

    def test_claim_sync_complete_are_one_in_process_semantic_path(self):
        claimed = self.protocol.next_task(repo_root=str(self.repo.root))
        self.assertEqual((claimed["status"], claimed["run_id"], claimed["lane_id"]), ("claimed", "compat-v2", "compat-v2-main"))
        self.assertLess(len(str(claimed).encode()), 8192)
        self.assertNotIn("claim_token", str(claimed))
        self.assertEqual(claimed["context"]["task_brief"]["objective"], "Implement A")
        self.assertIn("exclusive_paths", claimed["context"]["task_brief"]["scope"])
        handle = claimed["workflow_handle"]
        synced = self.protocol.coordinate_task(workflow_handle=handle, action="sync", payload={})
        self.assertEqual(synced["messages"], [])
        finished = self.protocol.finish_task(workflow_handle=handle, action="complete", disposition="implemented")
        self.assertEqual(finished["status"], "idle")
        with self.assertRaises(TodoError):
            self.locator.resolve(handle, required_operation="inspect_task")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='A'").fetchone()[0], "done")
            self.assertEqual(conn.execute("SELECT state FROM workflow_lanes WHERE id='compat-v2-main'").fetchone()[0], "closed")

    def test_lost_locator_is_resumed_by_next_task_without_raw_token(self):
        claimed = self.protocol.next_task(repo_root=str(self.repo.root))
        self.locator.forget(claimed["workflow_handle"])
        resumed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        self.assertEqual(resumed["status"], "resumed")
        self.assertNotEqual(resumed["workflow_handle"], claimed["workflow_handle"])

    def test_child_candidate_is_parent_mediated_and_never_completes_parent(self):
        claimed = self.protocol.next_task(repo_root=str(self.repo.root))
        delegated = self.protocol.delegate_task(
            workflow_handle=claimed["workflow_handle"], delegated_objective="Inspect one bounded source file", mode="readonly"
        )
        self.assertEqual(delegated["status"], "claimed")
        self.assertLessEqual(delegated["packet_size_bytes"], 4096)
        collected = self.protocol.collect_delegation(delegation_handle=delegated["delegation_handle"])
        self.assertFalse(collected["parent_task_completed"])
        accepted = self.protocol.coordinate_task(
            workflow_handle=claimed["workflow_handle"], action="accept_child",
            payload={"child_execution_id": delegated["child_execution_id"]},
        )
        self.assertEqual(accepted["state"], "accepted")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='A'").fetchone()[0], "in_progress")
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_lanes WHERE id=?", (delegated["child_execution_id"],)).fetchone()[0], 0)

    def test_arrival_schema_requires_full_provenance(self):
        with self.assertRaises(TodoError) as error:
            _validate_action("arrive", {"rendezvous_id": "R", "summary": "done"})
        self.assertEqual(error.exception.code, "invalid_coordination_payload")
        _validate_action("arrive", {
            "rendezvous_id": "R", "summary": "done", "base_source_identity": "base",
            "final_source_identity": "final", "artifact": {"kind": "commit", "ref": "abc"},
            "evidence": [{"type": "gate", "id": "G"}], "context_version": 1,
        })


if __name__ == "__main__":
    unittest.main()
