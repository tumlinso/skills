from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.front_door import require_mutation_route
from todo_orchestrator.models import TodoError
from todo_orchestrator.projections import atomic_write_json
from todo_orchestrator.service import Service
from todo_orchestrator.workflow.capabilities import WorkflowCapabilityLocator
from todo_orchestrator.workflow.protocol import WorkflowProtocol
from todo_orchestrator.workflow.service import WorkflowKernel


class WorkflowFrontDoorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        self.repo.apply(base_plan([safe_task("A", "src/a")]))

    def tearDown(self) -> None:
        self.repo.close()

    def migrate_identity(self) -> None:
        identity_path = self.repo.root / ".todo-orchestrator" / "project.json"
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        identity["configuration"]["workflow_front_door"] = "coding-workflow"
        atomic_write_json(identity_path, identity)

    def test_legacy_project_keeps_direct_automated_compatibility(self) -> None:
        claimed = self.repo.service.continue_work(task_id="A")
        self.assertEqual(claimed["claim"]["task_id"], "A")

    def test_migrated_project_blocks_direct_automated_mutation_but_not_reads(self) -> None:
        self.migrate_identity()
        service = Service(self.repo.root)
        self.assertEqual(service.status()["project_revision"], service.db.revision())
        with self.assertRaises(TodoError) as caught:
            service.continue_work(task_id="A")
        self.assertEqual(caught.exception.code, "workflow_front_door_required")
        self.assertEqual(caught.exception.details["workflow_front_door"], "coding-workflow")
        self.assertTrue(caught.exception.details["read_only_commands_available"])

    def test_cli_returns_stable_front_door_result(self) -> None:
        self.migrate_identity()
        status_process, status = self.repo.run("status")
        self.assertEqual(status_process.returncode, 0)
        self.assertTrue(status["ok"])
        claim_process, claim = self.repo.run("continue", "--task-id", "A")
        self.assertNotEqual(claim_process.returncode, 0)
        self.assertFalse(claim["ok"])
        self.assertEqual(claim["code"], "workflow_front_door_required")
        self.assertNotIn("token", json.dumps(claim).lower())

    def test_explicit_test_and_self_debug_modes_remain_available(self) -> None:
        self.migrate_identity()
        for mode in ("test", "self_debug"):
            require_mutation_route(
                {"configuration": {"workflow_front_door": "coding-workflow"}},
                operation="plan.applied",
                mutation_mode=mode,
                interactive=False,
            )
        claimed = Service(self.repo.root, mutation_mode="test").continue_work(task_id="A")
        self.assertEqual(claimed["claim"]["task_id"], "A")

    def test_interactive_owner_maintenance_has_no_approval_token(self) -> None:
        project = {"configuration": {"workflow_front_door": "coding-workflow"}}
        require_mutation_route(project, operation="plan.applied", interactive=True)
        with self.assertRaises(TodoError) as caught:
            require_mutation_route(project, operation="plan.applied", interactive=False)
        self.assertEqual(caught.exception.code, "workflow_front_door_required")
        self.assertNotIn("token", json.dumps(caught.exception.details).lower())

    def test_canonical_in_process_workflow_is_permitted(self) -> None:
        self.migrate_identity()
        locator_dir = tempfile.TemporaryDirectory()
        try:
            locator = WorkflowCapabilityLocator(Path(locator_dir.name))
            protocol = WorkflowProtocol(WorkflowKernel(locator=locator), locator)
            claimed = protocol.next_task(repo_root=str(self.repo.root), task_id="A")
            self.assertEqual(claimed["status"], "claimed")
            self.assertEqual(claimed["task_id"], "A")
        finally:
            locator_dir.cleanup()


if __name__ == "__main__":
    unittest.main()
