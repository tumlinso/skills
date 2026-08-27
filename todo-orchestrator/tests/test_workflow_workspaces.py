from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from todo_orchestrator.db import Database
from todo_orchestrator.models import TodoError
from todo_orchestrator.workflow.workspaces import WorkspaceService


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


class WorkflowWorkspaceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "source"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "workflow@example.invalid")
        git(self.repo, "config", "user.name", "Workflow Test")
        (self.repo / "shared.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
        git(self.repo, "add", "shared.txt")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")

        self.db = Database(self.root / "state.sqlite3")
        self.db.initialize({"project_uuid": "project-1", "project_name": "fixture"})

        def seed(conn, revision):
            now = "2026-08-27T00:00:00Z"
            for task_id in ("ROOT", "IMPL", "IMPL2", "INTEGRATE"):
                conn.execute(
                    "INSERT INTO tasks(id,kind,title,status,created_at,updated_at,revision) VALUES(?,?,?,?,?,?,?)",
                    (task_id, "workstream", task_id, "planned", now, now, revision),
                )
            conn.execute(
                "INSERT INTO workflow_runs(id,root_task_id,status,created_at,updated_at,revision) VALUES(?,?,?,?,?,?)",
                ("RUN", "ROOT", "active", now, now, revision),
            )
            lanes = (
                ("COORD", None, "coordinator", "exclusive"),
                ("PRODUCER", "COORD", "implementer", "isolated_merge"),
                ("PRODUCER2", "COORD", "implementer", "isolated_merge"),
                ("INTEGRATOR", "COORD", "integrator", "exclusive"),
                ("NOT_INTEGRATOR", "COORD", "implementer", "exclusive"),
                ("READER", "COORD", "validator", "read_shared"),
            )
            for lane_id, parent, role, mode in lanes:
                conn.execute(
                    """INSERT INTO workflow_lanes(
                         id,run_id,parent_lane_id,role,state,workspace_mode,created_at,updated_at,revision)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (lane_id, "RUN", parent, role, "ready", mode, now, now, revision),
                )

        self.db.mutate(
            actor_session_id=None,
            entity_type="fixture",
            entity_id="RUN",
            event_type="fixture_seeded",
            payload={},
            operation=seed,
        )
        self.managed = self.root / "managed"
        self.service = WorkspaceService(self.db, managed_root=self.managed)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def create_destination(self, *, lane: str = "INTEGRATOR") -> dict[str, object]:
        return self.service.create_workspace(
            repository_root=self.repo,
            repository_identity="repo-identity",
            run_id="RUN",
            lane_id=lane,
            mode="exclusive",
            base_commit=self.base,
            worktree_path=self.managed / lane.lower(),
            branch=f"test-{lane.lower()}",
            integration_task_id="INTEGRATE",
        )

    def create_producer(self, *, lane: str = "PRODUCER", base: str | None = None) -> dict[str, object]:
        return self.service.create_workspace(
            repository_root=self.repo,
            repository_identity="repo-identity",
            run_id="RUN",
            lane_id=lane,
            mode="isolated_merge",
            base_commit=base or self.base,
            worktree_path=self.managed / lane.lower(),
            branch=f"test-{lane.lower()}",
            integration_task_id="INTEGRATE",
        )

    def producer_commit(self, workspace: dict[str, object], content: str) -> str:
        path = Path(str(workspace["worktree_path"]))
        (path / "shared.txt").write_text(content, encoding="utf-8")
        git(path, "add", "shared.txt")
        git(path, "commit", "-qm", "producer change")
        return git(path, "rev-parse", "HEAD")

    def assert_code(self, expected: str, call) -> None:
        with self.assertRaises(TodoError) as caught:
            call()
        self.assertEqual(caught.exception.code, expected)

    def test_modes_materialize_only_managed_first_class_workspaces(self) -> None:
        destination = self.create_destination()
        self.assertTrue(Path(str(destination["worktree_path"])).is_dir())
        shared = self.service.create_workspace(
            repository_root=self.repo,
            repository_identity="repo-identity",
            run_id="RUN",
            lane_id="READER",
            mode="read_shared",
            base_commit=self.base,
            worktree_path=None,
            branch=None,
            integration_task_id=None,
        )
        self.assertIsNone(shared["worktree_path"])
        self.assert_code(
            "local_child_workspace_forbidden",
            lambda: self.service.create_workspace(
                repository_root=self.repo,
                repository_identity="repo-identity",
                run_id="RUN",
                lane_id="child-execution-id",
                mode="isolated_merge",
                base_commit=self.base,
                worktree_path=self.managed / "child",
                branch="child",
                integration_task_id="INTEGRATE",
                worker_class="child",
            ),
        )
        self.assertFalse((self.managed / "child").exists())

    def test_unmanaged_paths_and_mode_mismatch_are_rejected_before_git(self) -> None:
        self.assert_code(
            "workspace_path_unmanaged",
            lambda: self.service.create_workspace(
                repository_root=self.repo,
                repository_identity="repo-identity",
                run_id="RUN",
                lane_id="PRODUCER",
                mode="isolated_merge",
                base_commit=self.base,
                worktree_path=self.root / "outside",
                branch="outside",
                integration_task_id="INTEGRATE",
            ),
        )
        self.assert_code(
            "lane_workspace_mode_mismatch",
            lambda: self.service.create_workspace(
                repository_root=self.repo,
                repository_identity="repo-identity",
                run_id="RUN",
                lane_id="PRODUCER",
                mode="exclusive",
                base_commit=self.base,
                worktree_path=self.managed / "wrong-mode",
                branch="wrong-mode",
                integration_task_id="INTEGRATE",
            ),
        )

    def test_exact_same_base_is_enforced_for_isolated_participants(self) -> None:
        self.create_producer()
        (self.repo / "later.txt").write_text("later\n", encoding="utf-8")
        git(self.repo, "add", "later.txt")
        git(self.repo, "commit", "-qm", "later base")
        later = git(self.repo, "rev-parse", "HEAD")
        self.assert_code("workspace_base_mismatch", lambda: self.create_producer(lane="PRODUCER2", base=later))
        self.assertFalse((self.managed / "producer2").exists())

    def test_commit_artifact_queue_merge_gates_and_explicit_cleanup_eligibility(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha changed\nbeta\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        self.assertEqual(len(str(artifact["diff_hash"])), 64)
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        applied = self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.assertEqual(applied["state"], "awaiting_gates")
        self.assertEqual((Path(str(destination["worktree_path"])) / "shared.txt").read_text(), "alpha changed\nbeta\ngamma\n")
        finished = self.service.record_post_merge_gates(
            queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "status": "passed"}]
        )
        self.assertEqual(finished["state"], "integrated")
        eligible = self.service.mark_cleanup_eligible(workspace_id=str(producer["workspace_id"]))
        self.assertTrue(eligible["cleanup_eligible"])
        self.assertFalse(eligible["deleted"])
        self.assertTrue(Path(str(producer["worktree_path"])).exists())
        self.assert_code(
            "workspace_dirty_preserved",
            lambda: self.service.mark_cleanup_eligible(workspace_id=str(destination["workspace_id"])),
        )
        self.assertTrue(Path(str(destination["worktree_path"])).exists())

    def test_integrator_role_and_exclusive_destination_are_authoritative(self) -> None:
        self.create_destination(lane="NOT_INTEGRATOR")
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta changed\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        self.assert_code(
            "integrator_role_required",
            lambda: self.service.enqueue_artifact(
                artifact_id=str(artifact["artifact_id"]),
                integrator_lane_id="NOT_INTEGRATOR",
                integration_task_id="INTEGRATE",
            ),
        )

    def test_real_merge_conflict_becomes_preserved_integration_work(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "producer\nbeta\ngamma\n")
        destination_path = Path(str(destination["worktree_path"]))
        (destination_path / "shared.txt").write_text("integrator\nbeta\ngamma\n", encoding="utf-8")
        git(destination_path, "add", "shared.txt")
        git(destination_path, "commit", "-qm", "integrator conflicting change")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        result = self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.assertEqual(result["state"], "conflict")
        self.assertEqual(result["integration_task_id"], "INTEGRATE")
        self.assertIn("shared.txt", result["conflict"]["paths"])
        self.assertTrue(result["conflict"]["preserved"])
        self.assertTrue(destination_path.exists())
        self.assertIn("UU shared.txt", git(destination_path, "status", "--porcelain=v1"))

    def test_patch_hash_is_revalidated_and_changed_artifact_is_refused(self) -> None:
        self.create_destination()
        producer = self.create_producer()
        producer_path = Path(str(producer["worktree_path"]))
        (producer_path / "shared.txt").write_text("alpha\nbeta\npatch\n", encoding="utf-8")
        patch = self.managed / "immutable.patch"
        patch.write_bytes(subprocess.run(
            ["git", "-C", str(producer_path), "diff", "--binary"], capture_output=True, check=True
        ).stdout)
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="patch", artifact_ref=str(patch)
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        patch.write_text("changed after publication\n", encoding="utf-8")
        self.assert_code("artifact_content_changed", lambda: self.service.apply_next(queue_id=str(queued["queue_id"])))

    def test_failed_post_merge_gate_preserves_destination_and_blocks_cleanup(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta\ngamma changed\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        self.service.apply_next(queue_id=str(queued["queue_id"]))
        result = self.service.record_post_merge_gates(
            queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "status": "failed"}]
        )
        self.assertEqual(result["state"], "gate_failed")
        self.assertTrue(Path(str(destination["worktree_path"])).exists())
        self.assert_code(
            "workspace_cleanup_not_terminal",
            lambda: self.service.mark_cleanup_eligible(workspace_id=str(producer["workspace_id"])),
        )


if __name__ == "__main__":
    unittest.main()
