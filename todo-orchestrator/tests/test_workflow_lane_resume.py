from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.workflow.capabilities import WorkflowCapabilityLocator
from todo_orchestrator.workflow.protocol import WorkflowProtocol
from todo_orchestrator.workflow.recovery import RecoveryEngine
from todo_orchestrator.workflow.service import WorkflowKernel


class WorkflowLaneResumeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        (self.repo.root / "src" / "a").mkdir(parents=True)
        (self.repo.root / "src" / "a" / "unit.txt").write_text("base\n", encoding="utf-8")
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        self.locator_temp = tempfile.TemporaryDirectory()
        self.locator = WorkflowCapabilityLocator(Path(self.locator_temp.name))
        self.protocol = WorkflowProtocol(WorkflowKernel(locator=self.locator), self.locator)
        self.old_thread = os.environ.get("CODEX_THREAD_ID")
        os.environ["CODEX_THREAD_ID"] = "lane-resume-test"

    def tearDown(self) -> None:
        if self.old_thread is None:
            os.environ.pop("CODEX_THREAD_ID", None)
        else:
            os.environ["CODEX_THREAD_ID"] = self.old_thread
        self.locator_temp.cleanup()
        self.repo.close()

    def lane_state(self) -> tuple[str, str]:
        with self.repo.service.db.read() as conn:
            lane = conn.execute("SELECT state FROM workflow_lanes WHERE id='compat-v2-main'").fetchone()[0]
            task = conn.execute(
                "SELECT state FROM workflow_lane_tasks WHERE lane_id='compat-v2-main' AND task_id='A'"
            ).fetchone()[0]
        return lane, task

    def test_release_and_handoff_requeue_the_same_serial_head(self) -> None:
        for action in ("release", "handoff"):
            with self.subTest(action=action):
                claimed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
                finished = self.protocol.finish_task(
                    workflow_handle=claimed["workflow_handle"], action=action,
                    disposition="validated", reason="nonterminal", note="preserved handoff",
                )
                self.assertTrue(finished["terminal"])
                self.assertEqual(self.lane_state(), ("ready", "queued"))
                resumed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
                self.assertEqual(resumed["status"], "claimed")
                self.protocol.finish_task(
                    workflow_handle=resumed["workflow_handle"], action="release",
                    disposition="validated", reason="next subtest",
                )

    def test_block_requeues_but_keeps_lane_explicitly_attention_required(self) -> None:
        claimed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        self.protocol.finish_task(
            workflow_handle=claimed["workflow_handle"], action="block",
            disposition="failed", reason="needs owner", note="blocked",
        )
        self.assertEqual(self.lane_state(), ("attention_required", "queued"))
        self.assertEqual(self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")["status"], "idle")
        engine = RecoveryEngine(
            self.repo.service.db, self.repo.root, str(self.repo.service.project["project_uuid"]),
            process_probe=lambda hostname, pid, process_start: False,
        )
        plan = engine.inspect("A")
        self.assertEqual([item["kind"] for item in plan["actions"]], ["requeue_blocked_task"])
        recovered = engine.execute(plan, "resolved the recorded blocking condition")
        self.assertEqual(recovered["resume"], "next_task")
        self.assertEqual(self.lane_state(), ("ready", "queued"))
        resumed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        self.assertEqual(resumed["status"], "claimed")

    def test_clean_owner_recovery_requeues_and_next_task_reissues_capability(self) -> None:
        claimed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        engine = RecoveryEngine(
            self.repo.service.db, self.repo.root, str(self.repo.service.project["project_uuid"]),
            process_probe=lambda hostname, pid, process_start: False,
        )
        result = engine.execute(engine.inspect("A"), "stopped clean first-class worker")
        self.assertEqual(result["resume"], "next_task")
        self.assertFalse(result["files_mutated"])
        self.assertEqual(self.lane_state(), ("ready", "queued"))
        resumed = self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        self.assertEqual(resumed["status"], "claimed")
        self.assertNotEqual(resumed["workflow_handle"], claimed["workflow_handle"])

    def test_dirty_owner_recovery_preserves_files_and_lane_attention(self) -> None:
        self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")
        dirty = self.repo.root / "src" / "a" / "unit.txt"
        dirty.write_text("preserve dirty\n", encoding="utf-8")
        before = dirty.read_bytes()
        engine = RecoveryEngine(
            self.repo.service.db, self.repo.root, str(self.repo.service.project["project_uuid"]),
            process_probe=lambda hostname, pid, process_start: False,
        )
        result = engine.execute(engine.inspect("A"), "paused dirty first-class worker")
        self.assertEqual(dirty.read_bytes(), before)
        self.assertIn("A", result["dirty_tasks"])
        self.assertEqual(self.lane_state(), ("attention_required", "queued"))
        self.assertEqual(self.protocol.next_task(repo_root=str(self.repo.root), task_id="A")["status"], "idle")


if __name__ == "__main__":
    unittest.main()
