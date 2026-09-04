from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from todo_orchestrator.db import Database
from todo_orchestrator.config import utc_now
from todo_orchestrator.claims import claim_best
from todo_orchestrator.gates import run_gate
from todo_orchestrator.models import ProjectPaths, TodoError
from todo_orchestrator.sessions import create_session
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
            conn.executemany(
                "INSERT INTO workflow_lane_tasks(lane_id,position,task_id,state,enqueued_at,revision) "
                "VALUES(?,?,?,'queued',?,?)",
                [
                    ("PRODUCER", 0, "IMPL", now, revision),
                    ("PRODUCER2", 0, "IMPL2", now, revision),
                    ("INTEGRATOR", 0, "INTEGRATE", now, revision),
                    ("NOT_INTEGRATOR", 0, "INTEGRATE", now, revision),
                ],
            )
            conn.execute(
                "INSERT INTO gates(id,task_id,type,config_json,required,status,valid,revision) "
                "VALUES('POST','INTEGRATE','manual','{}',1,'pending',0,?)",
                (revision,),
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
        self.service = WorkspaceService(
            self.db,
            managed_root=self.managed,
            repository_identity_resolver=lambda root: "repo-identity",
        )

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

    def gate_evidence(self, status: str) -> str:
        evidence_id = f"POST-{status}-{self.db.revision()}"
        valid = int(status == "passed")
        with self.db.read() as conn:
            queue = conn.execute(
                "SELECT q.merge_result_json,d.worktree_path FROM workflow_integration_queue q "
                "JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id "
                "WHERE q.state='awaiting_gates'"
            ).fetchone()
        applied = json.loads(queue["merge_result_json"])
        fingerprint = f"fingerprint-{evidence_id}"
        metadata = json.dumps({
            "input_fingerprint": fingerprint,
            "started_revision": self.db.revision(),
            "workspace_path": str(Path(queue["worktree_path"]).resolve()),
            "source_identity": applied["source_identity"],
        }, sort_keys=True)
        def operation(conn, revision):
            conn.execute(
                "UPDATE gates SET status=?,valid=?,input_fingerprint=?,revision=? WHERE id='POST'",
                (status, valid, fingerprint, revision),
            )
            conn.execute(
                "INSERT INTO evidence(id,gate_id,kind,status,metadata_json,created_at,revision) "
                "VALUES(?,'POST','gate',?,?,?,?)",
                (evidence_id, status, metadata, utc_now(), revision),
            )
        self.db.mutate(actor_session_id=None, entity_type="gate", entity_id="POST", event_type="test_gate", payload={}, operation=operation)
        return evidence_id

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
        insecure = WorkspaceService(self.db, managed_root=self.managed)
        self.assert_code(
            "repository_identity_resolver_required",
            lambda: insecure.create_workspace(
                repository_root=self.repo, repository_identity="caller-asserted", run_id="RUN",
                lane_id="PRODUCER", mode="isolated_merge", base_commit=self.base,
                worktree_path=self.managed / "unverified", branch="unverified",
                integration_task_id="INTEGRATE",
            ),
        )
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
        enforcing = WorkspaceService(
            self.db,
            managed_root=self.managed,
            repository_identity_resolver=lambda root: "authoritative-repo",
        )
        self.assert_code(
            "repository_identity_mismatch",
            lambda: enforcing.create_workspace(
                repository_root=self.repo, repository_identity="caller-asserted", run_id="RUN",
                lane_id="PRODUCER", mode="isolated_merge", base_commit=self.base,
                worktree_path=self.managed / "identity-mismatch", branch="identity-mismatch",
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
            queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}]
        )
        self.assertEqual(finished["state"], "integrated")
        eligible = self.service.mark_cleanup_eligible(workspace_id=str(producer["workspace_id"]))
        self.assertTrue(eligible["cleanup_eligible"])
        self.assertFalse(eligible["deleted"])
        self.assertTrue(Path(str(producer["worktree_path"])).exists())
        destination_eligible = self.service.mark_cleanup_eligible(workspace_id=str(destination["workspace_id"]))
        self.assertTrue(destination_eligible["cleanup_eligible"])
        self.assertTrue(Path(str(destination["worktree_path"])).exists())

    def test_two_producer_artifacts_integrate_serially_into_one_destination(self) -> None:
        destination = self.create_destination()
        first = self.create_producer()
        second = self.create_producer(lane="PRODUCER2")
        first_commit = self.producer_commit(first, "alpha changed\nbeta\ngamma\n")
        second_commit = self.producer_commit(second, "alpha\nbeta\ngamma changed\n")
        first_artifact = self.service.publish_artifact(
            workspace_id=str(first["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=first_commit
        )
        second_artifact = self.service.publish_artifact(
            workspace_id=str(second["workspace_id"]), task_id="IMPL2", kind="commit", artifact_ref=second_commit
        )
        first_queue = self.service.enqueue_artifact(
            artifact_id=str(first_artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        second_queue = self.service.enqueue_artifact(
            artifact_id=str(second_artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        self.service.apply_next(queue_id=str(first_queue["queue_id"]))
        first_result = self.service.record_post_merge_gates(
            queue_id=str(first_queue["queue_id"]),
            gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}],
        )
        destination_path = Path(str(destination["worktree_path"]))
        self.assertEqual(git(destination_path, "rev-parse", "HEAD"), first_result["integrated_artifact"]["ref"])
        self.assertEqual(git(destination_path, "status", "--porcelain=v1"), "")

        self.service.apply_next(queue_id=str(second_queue["queue_id"]))
        second_result = self.service.record_post_merge_gates(
            queue_id=str(second_queue["queue_id"]),
            gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}],
        )
        self.assertEqual(git(destination_path, "rev-parse", "HEAD"), second_result["integrated_artifact"]["ref"])
        self.assertEqual(git(destination_path, "status", "--porcelain=v1"), "")
        self.assertEqual(
            (destination_path / "shared.txt").read_text(encoding="utf-8"),
            "alpha changed\nbeta\ngamma changed\n",
        )

    def test_commit_artifact_applies_the_complete_base_to_tip_range(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        producer_path = Path(str(producer["worktree_path"]))
        (producer_path / "first.txt").write_text("first\n", encoding="utf-8")
        git(producer_path, "add", "first.txt")
        git(producer_path, "commit", "-qm", "first producer commit")
        (producer_path / "second.txt").write_text("second\n", encoding="utf-8")
        git(producer_path, "add", "second.txt")
        git(producer_path, "commit", "-qm", "second producer commit")
        tip = git(producer_path, "rev-parse", "HEAD")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=tip
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        applied = self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.assertEqual(applied["state"], "awaiting_gates")
        destination_path = Path(str(destination["worktree_path"]))
        self.assertEqual((destination_path / "first.txt").read_text(), "first\n")
        self.assertEqual((destination_path / "second.txt").read_text(), "second\n")

    def test_canonical_gate_runner_binds_destination_workspace_and_source(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha changed\nbeta\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        applied = self.service.apply_next(queue_id=str(queued["queue_id"]))

        def authorize(conn, revision):
            conn.execute(
                "UPDATE gates SET type='command',config_json=? WHERE id='POST'",
                (json.dumps({
                    "argv": [sys.executable, "-c", "from pathlib import Path; assert Path('shared.txt').read_text().startswith('alpha changed')"],
                    "input_paths": ["shared.txt"],
                }, sort_keys=True),),
            )
            session, _ = create_session(conn, self.repo)
            _, claim_token = claim_best(
                conn, self.repo, str(session["agent_id"]), revision, 7200,
                requested_task_id="INTEGRATE", reconcile_expired=False,
            )
            return claim_token

        claim_token, _ = self.db.mutate(
            actor_session_id=None, entity_type="fixture", entity_id="INTEGRATE",
            event_type="fixture_gate_authorized", payload={}, operation=authorize,
        )
        evidence_dir = self.root / "evidence"
        evidence_dir.mkdir()
        paths = ProjectPaths(
            repo_root=self.repo,
            control_dir=self.root / "control",
            project_file=self.root / "project.json",
            snapshot_file=self.root / "snapshot.json",
            state_dir=self.root,
            db_file=self.root / "state.sqlite3",
            evidence_dir=evidence_dir,
        )
        gate, _ = run_gate(
            self.db,
            paths,
            {"configuration": {}},
            "POST",
            claim_token,
            execution_root=Path(str(destination["worktree_path"])),
            workspace_base_commit=self.base,
        )
        self.assertEqual(gate["status"], "passed")
        finished = self.service.record_post_merge_gates(
            queue_id=str(queued["queue_id"]),
            gate_results=[{"gate_id": "POST", "evidence_id": gate["evidence_id"]}],
        )
        self.assertEqual(finished["state"], "integrated")
        self.assertEqual(finished["integrated_artifact"]["kind"], "commit")
        self.assertEqual(
            _sha := subprocess.run(
                ["git", "-C", str(destination["worktree_path"]), "rev-parse", f"{finished['integrated_artifact']['ref']}^{{commit}}"],
                capture_output=True, text=True, check=True,
            ).stdout.strip(),
            finished["integrated_artifact"]["ref"],
        )

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
        pre_apply_head = git(destination_path, "rev-parse", "HEAD")
        cherry_pick_head = Path(git(destination_path, "rev-parse", "--git-path", "CHERRY_PICK_HEAD"))
        if cherry_pick_head.exists():
            cherry_pick_head.unlink()
        retried = self.service.retry_conflict(queue_id=str(queued["queue_id"]))
        self.assertEqual(retried["state"], "queued")
        self.assertEqual(retried["restored_head"], pre_apply_head)
        self.assertEqual(git(destination_path, "status", "--porcelain=v1"), "")
        self.assertEqual(git(destination_path, "rev-parse", "HEAD"), pre_apply_head)

    def test_patch_is_copied_to_immutable_managed_artifact(self) -> None:
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
        self.assertEqual(self.service.apply_next(queue_id=str(queued["queue_id"]))["state"], "awaiting_gates")

    def test_failed_post_merge_gate_preserves_destination_and_blocks_cleanup(self) -> None:
        (self.repo / ".todo-orchestrator").mkdir()
        (self.repo / ".todo-orchestrator" / "state.snapshot.json").write_text("{}\n", encoding="utf-8")
        git(self.repo, "add", ".todo-orchestrator/state.snapshot.json")
        git(self.repo, "commit", "-qm", "tracked authority projection")
        self.base = git(self.repo, "rev-parse", "HEAD")
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
            queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("failed")}]
        )
        self.assertEqual(result["state"], "gate_failed")
        self.assertTrue(Path(str(destination["worktree_path"])).exists())
        destination_path = Path(str(destination["worktree_path"]))
        snapshot = destination_path / ".todo-orchestrator" / "state.snapshot.json"
        snapshot.write_text(snapshot.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        retried_projection_refresh = self.service.retry_failed_gates(queue_id=str(queued["queue_id"]))
        self.assertEqual(retried_projection_refresh["state"], "awaiting_gates")
        self.assertEqual(
            self.service.record_post_merge_gates(
                queue_id=str(queued["queue_id"]),
                gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("failed")}],
            )["state"],
            "gate_failed",
        )
        (destination_path / "resolution.txt").write_text("integrator resolution\n", encoding="utf-8")
        git(destination_path, "add", "resolution.txt")
        self.assert_code(
            "integration_source_changed",
            lambda: self.service.retry_failed_gates(queue_id=str(queued["queue_id"])),
        )
        retried = self.service.retry_failed_gates(
            queue_id=str(queued["queue_id"]), allow_source_resolution=True
        )
        self.assertEqual(retried["state"], "awaiting_gates")
        finalized = self.service.record_post_merge_gates(
            queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}]
        )
        self.assertEqual(finalized["state"], "integrated")
        self.assertTrue(self.service.mark_cleanup_eligible(workspace_id=str(producer["workspace_id"]))["cleanup_eligible"])

    def test_finalization_failure_can_return_to_authoritative_gates(self) -> None:
        self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta\ngamma retry\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        self.service.apply_next(queue_id=str(queued["queue_id"]))
        with mock.patch.object(
            self.service,
            "_freeze_integration_commit",
            side_effect=TodoError("integration_tree_mismatch", "fixture finalization failure"),
        ):
            self.assert_code(
                "integration_tree_mismatch",
                lambda: self.service.record_post_merge_gates(
                    queue_id=str(queued["queue_id"]),
                    gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}],
                ),
            )
        with self.db.read() as conn:
            self.assertEqual(
                conn.execute(
                    "SELECT state FROM workflow_integration_queue WHERE id=?",
                    (queued["queue_id"],),
                ).fetchone()[0],
                "finalization_failed",
            )
        retried = self.service.retry_finalization_failed(queue_id=str(queued["queue_id"]))
        self.assertEqual(retried["state"], "awaiting_gates")
        finalized = self.service.record_post_merge_gates(
            queue_id=str(queued["queue_id"]),
            gate_results=[{"gate_id": "POST", "evidence_id": self.gate_evidence("passed")}],
        )
        self.assertEqual(finalized["state"], "integrated")

    def test_caller_asserted_gate_status_cannot_authorize_integration(self) -> None:
        self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta asserted\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.db.mutate(
            actor_session_id=None, entity_type="evidence", entity_id="STALE", event_type="test_timestamp_adjusted", payload={},
            operation=lambda conn, revision: conn.execute(
                "UPDATE evidence SET created_at='9999-12-31T23:59:59Z' WHERE id='STALE'"
            ),
        )
        self.assert_code(
            "integration_gate_provenance_invalid",
            lambda: self.service.record_post_merge_gates(
                queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "status": "passed"}]
            ),
        )

    def test_gate_started_before_apply_and_changed_destination_are_rejected(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta provenance\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        destination_path = Path(str(destination["worktree_path"])).resolve()
        started_revision = self.db.revision()
        stale_metadata = json.dumps({
            "input_fingerprint": "stale-fingerprint",
            "started_revision": started_revision,
            "workspace_path": str(destination_path),
            "source_identity": self.service._source_identity(destination_path, self.base),
        }, sort_keys=True)
        self.db.mutate(
            actor_session_id=None, entity_type="gate", entity_id="POST", event_type="stale_gate", payload={},
            operation=lambda conn, revision: (
                conn.execute("UPDATE gates SET status='passed',valid=1,input_fingerprint='stale-fingerprint',revision=? WHERE id='POST'", (revision,)),
                conn.execute(
                    "INSERT INTO evidence(id,gate_id,kind,status,metadata_json,created_at,revision) "
                    "VALUES('STALE','POST','gate','passed',?,?,?)",
                    (stale_metadata, utc_now(), revision),
                ),
            ),
        )
        self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.assert_code(
            "integration_gate_workspace_mismatch",
            lambda: self.service.record_post_merge_gates(
                queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": "STALE"}]
            ),
        )

        evidence = self.gate_evidence("passed")
        (destination_path / "shared.txt").write_text("changed after gates\n", encoding="utf-8")
        self.assert_code(
            "integration_source_changed",
            lambda: self.service.record_post_merge_gates(
                queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": evidence}]
            ),
        )

    def test_all_required_gates_are_mandatory_and_apply_failure_is_recorded(self) -> None:
        destination = self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta coverage\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        destination_path = Path(str(destination["worktree_path"]))
        (destination_path / "dirty.txt").write_text("preserve\n", encoding="utf-8")
        self.assert_code("integration_workspace_dirty", lambda: self.service.apply_next(queue_id=str(queued["queue_id"])))
        with self.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM workflow_integration_queue WHERE id=?", (queued["queue_id"],)).fetchone()[0], "apply_failed")
            self.assertEqual(conn.execute("SELECT state FROM workflow_workspaces WHERE id=?", (destination["workspace_id"],)).fetchone()[0], "apply_failed")
        self.assert_code(
            "integration_workspace_dirty",
            lambda: self.service.retry_apply_failed(queue_id=str(queued["queue_id"])),
        )
        (destination_path / "dirty.txt").unlink()
        retried = self.service.retry_apply_failed(queue_id=str(queued["queue_id"]))
        self.assertEqual(retried["state"], "queued")
        self.assertEqual(retried["destination_state"], "active")
        applied = self.service.apply_next(queue_id=str(queued["queue_id"]))
        self.assertEqual(applied["state"], "awaiting_gates")

        # A fresh fixture flow proves omitting any required gate cannot authorize integration.
        self.tearDown()
        self.setUp()
        self.db.mutate(
            actor_session_id=None, entity_type="gate", entity_id="POST2", event_type="test_gate_added", payload={},
            operation=lambda conn, revision: conn.execute(
                "INSERT INTO gates(id,task_id,type,config_json,required,status,valid,revision) "
                "VALUES('POST2','INTEGRATE','manual','{}',1,'pending',0,?)", (revision,)
            ),
        )
        self.create_destination()
        producer = self.create_producer()
        commit = self.producer_commit(producer, "alpha\nbeta gates\ngamma\n")
        artifact = self.service.publish_artifact(
            workspace_id=str(producer["workspace_id"]), task_id="IMPL", kind="commit", artifact_ref=commit
        )
        queued = self.service.enqueue_artifact(
            artifact_id=str(artifact["artifact_id"]), integrator_lane_id="INTEGRATOR", integration_task_id="INTEGRATE"
        )
        self.service.apply_next(queue_id=str(queued["queue_id"]))
        evidence = self.gate_evidence("passed")
        self.assert_code(
            "integration_gate_coverage_incomplete",
            lambda: self.service.record_post_merge_gates(
                queue_id=str(queued["queue_id"]), gate_results=[{"gate_id": "POST", "evidence_id": evidence}]
            ),
        )


if __name__ == "__main__":
    unittest.main()
