from __future__ import annotations

import io
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.models import TodoError
from todo_orchestrator.workflow.admin import inspect_owner_recovery, run_owner_recovery
from todo_orchestrator.workflow.recovery import RecoveryEngine, project_recovery_lock


class TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


class WorkflowRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        self.repo.apply(base_plan([
            safe_task("A", "src/a", priority=10),
            safe_task("T", "src/t", checkpoints=[{"id": "T-DONE", "title": "T done"}]),
        ]))
        self.capsule = self.repo.service.continue_work(task_id="A")
        self.claim_id = self.capsule["claim"]["claim_id"]
        self.session_id = self.capsule["session"]["agent_id"]
        self.project_uuid = str(self.repo.service.project["project_uuid"])

    def tearDown(self) -> None:
        self.repo.close()

    def mutate(self, operation):
        return self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="recovery_fixture",
            entity_id="A",
            event_type="recovery_fixture.seeded",
            payload={},
            operation=operation,
        )[0]

    def engine(self, probe=None) -> RecoveryEngine:
        return RecoveryEngine(
            self.repo.service.db,
            self.repo.root,
            self.project_uuid,
            process_probe=probe or (lambda hostname, pid, started: False),
            actor_identity="test-owner",
        )

    def seed_dispatch(self, *, pid: int = 999999, workspace: bool = False, capability: bool = False) -> None:
        def seed(conn, revision):
            conn.execute("INSERT INTO workflow_runs(id,root_task_id,created_at,updated_at,revision) VALUES('RUN','A','now','now',?)", (revision,))
            conn.execute("INSERT INTO workflow_lanes(id,run_id,role,created_at,updated_at,revision) VALUES('LANE','RUN','implementer','now','now',?)", (revision,))
            workspace_id = None
            if workspace:
                workspace_id = "WS"
                conn.execute(
                    "INSERT INTO workflow_workspaces(id,repository_identity,run_id,lane_id,mode,base_commit,worktree_path,branch,state,created_at,updated_at) "
                    "VALUES('WS','repo','RUN','LANE','isolated_merge','base',?,'branch','dirty','now','now')",
                    (str(self.repo.root),),
                )
            conn.execute(
                "INSERT INTO workflow_dispatches(id,lane_id,session_id,claim_id,workspace_id,context_version,heartbeat_at,hostname,pid,created_at,revision) "
                "VALUES('DISPATCH','LANE',?,?,?,1,'2000-01-01T00:00:00Z',?,?,'now',?)",
                (self.session_id, self.claim_id, workspace_id, socket.gethostname(), pid, revision),
            )
            if capability:
                conn.execute(
                    "INSERT INTO workflow_capabilities(id,token_hash,capability_class,project_uuid,repository_identity,session_id,claim_id,run_id,lane_id,role,task_id,allowed_operations_json,state,created_at,expires_at) "
                    "VALUES('CAP','hash-only','first_class',?,'repo',?,?,'RUN','LANE','implementer','A','[\"sync\"]','active','now','2999-01-01T00:00:00Z')",
                    (self.project_uuid, self.session_id, self.claim_id),
                )
        self.mutate(seed)

    def test_stopped_first_class_worker_clean_scope_retires_lineage_and_is_idempotent(self) -> None:
        self.seed_dispatch(capability=True)
        engine = self.engine()
        plan = engine.inspect("A")
        self.assertEqual(plan["status"], "recovery_needed")
        self.assertEqual(plan["blockers"], [])
        kinds = {item["kind"] for item in plan["actions"]}
        self.assertTrue({"retire_dispatch", "release_claim", "retire_capability"} <= kinds)
        result = engine.execute(plan, "stopped owner toc_secret-value")
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["resume"], "next_task")
        self.assertFalse(result["files_mutated"])
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM workflow_dispatches WHERE id='DISPATCH'").fetchone()[0], "recovered")
            self.assertEqual(conn.execute("SELECT state FROM claims WHERE id=?", (self.claim_id,)).fetchone()[0], "recovered_released")
            self.assertEqual(conn.execute("SELECT state FROM workflow_capabilities WHERE id='CAP'").fetchone()[0], "retired")
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='A'").fetchone()[0], "planned")
            audit = conn.execute("SELECT reason FROM workflow_recovery_audit").fetchone()
            event = conn.execute("SELECT payload_json FROM events WHERE event_type='workflow_recovery.completed'").fetchone()
        self.assertEqual(audit["reason"], "stopped owner [redacted]")
        self.assertNotIn("token", event[0].lower())
        second = engine.execute(engine.inspect("A"), "repeat")
        self.assertTrue(second["idempotent_noop"])
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM workflow_recovery_audit").fetchone()[0], 1)

    def test_lost_capability_index_does_not_prevent_resume(self) -> None:
        self.seed_dispatch(capability=False)
        result = self.engine().execute(self.engine().inspect("A"), "lost locator and handle")
        self.assertEqual(result["resume"], "next_task")
        self.assertEqual(result["status"], "recovered")

    def test_global_recovery_clears_attention_left_by_released_lane_claim(self) -> None:
        self.seed_dispatch()

        def release_with_attention(conn, revision):
            conn.execute("UPDATE claims SET state='released',released_at='now' WHERE id=?", (self.claim_id,))
            conn.execute("UPDATE workflow_dispatches SET state='released',released_at='now' WHERE id='DISPATCH'")
            conn.execute("UPDATE workflow_lanes SET state='ready' WHERE id='LANE'")
            conn.execute("INSERT INTO workflow_lane_tasks(lane_id,position,task_id,state,enqueued_at,revision) VALUES('LANE',0,'A','queued','now',?)", (revision,))
            conn.execute("UPDATE tasks SET status='in_progress',attention_reason='historical release note' WHERE id='A'")

        self.mutate(release_with_attention)
        engine = self.engine()
        plan = engine.inspect()
        self.assertIn(
            {"kind": "clear_released_attention", "task_id": "A"},
            plan["actions"],
        )
        engine.execute(plan, "clear released lane residue")
        with self.repo.service.db.read() as conn:
            task = conn.execute("SELECT status,attention_reason FROM tasks WHERE id='A'").fetchone()
        self.assertEqual(tuple(task), ("in_progress", None))

    def test_dirty_scope_and_workspace_are_quarantined_without_file_loss(self) -> None:
        self.seed_dispatch(workspace=True)
        source = self.repo.root / "src" / "a" / "dirty.txt"
        source.parent.mkdir(parents=True)
        source.write_text("preserve me\n", encoding="utf-8")
        before = source.read_bytes()
        plan = self.engine().inspect("A")
        self.assertTrue(any(item.get("dirty") for item in plan["actions"] if item["kind"] == "release_claim"))
        result = self.engine().execute(plan, "paused dirty worker")
        self.assertEqual(source.read_bytes(), before)
        self.assertIn("A", result["dirty_tasks"])
        with self.repo.service.db.read() as conn:
            task = conn.execute("SELECT status,attention_reason FROM tasks WHERE id='A'").fetchone()
            handoff = conn.execute("SELECT kind,payload_json FROM handoffs WHERE task_id='A' ORDER BY revision DESC LIMIT 1").fetchone()
            workspace = conn.execute("SELECT state,cleanup_eligible FROM workflow_workspaces WHERE id='WS'").fetchone()
        self.assertEqual(task["status"], "attention_required")
        self.assertEqual(handoff["kind"], "recovery_quarantine")
        self.assertIn("fingerprint", json.loads(handoff["payload_json"]))
        self.assertEqual(tuple(workspace), ("quarantined", 0))

    def test_live_or_unobservable_first_class_process_refuses_recovery(self) -> None:
        for observed in (True, None):
            with self.subTest(observed=observed):
                other = V2Repo()
                try:
                    other.apply(base_plan([safe_task("A", "src/a")]))
                    capsule = other.service.continue_work(task_id="A")
                    project_uuid = str(other.service.project["project_uuid"])
                    def seed(conn, revision):
                        conn.execute("INSERT INTO workflow_runs(id,root_task_id,created_at,updated_at,revision) VALUES('RUN','A','now','now',?)", (revision,))
                        conn.execute("INSERT INTO workflow_lanes(id,run_id,role,created_at,updated_at,revision) VALUES('LANE','RUN','implementer','now','now',?)", (revision,))
                        conn.execute(
                            "INSERT INTO workflow_dispatches(id,lane_id,session_id,claim_id,context_version,heartbeat_at,hostname,pid,created_at,revision) VALUES('D','LANE',?,?,1,'2999-01-01T00:00:00Z','remote',7,'now',?)",
                            (capsule["session"]["agent_id"], capsule["claim"]["claim_id"], revision),
                        )
                    other.service.db.mutate(actor_session_id=None, entity_type="fixture", entity_id="A", event_type="fixture", payload={}, operation=seed)
                    engine = RecoveryEngine(other.service.db, other.root, project_uuid, process_probe=lambda h, p, s, value=observed: value)
                    plan = engine.inspect("A")
                    self.assertEqual(plan["status"], "refused")
                    with self.assertRaises(TodoError) as error:
                        engine.execute(plan, "must refuse")
                    self.assertEqual(error.exception.code, "recovery_live_work_refused")
                finally:
                    other.close()

    def seed_child(self, *, expires_at: str, state: str = "running", candidate: bool = True) -> None:
        def seed(conn, revision):
            conn.execute(
                "INSERT INTO child_executions(id,parent_claim_id,task_id,objective,state,max_attempts,attempt_count,created_at,access_mode,authorized_scopes_json) "
                "VALUES('CHILD',?,'A','bounded',?,1,1,'now','write','[\"src/a\"]')",
                (self.claim_id, state),
            )
            conn.execute("INSERT INTO child_scope_leases(child_execution_id,path,state,acquired_at) VALUES('CHILD','src/a','active','now')")
            conn.execute(
                "INSERT INTO child_attempts(id,child_execution_id,attempt_number,token_hash,state,created_at,heartbeat_at,expires_at) VALUES('ATTEMPT','CHILD',1,'child-hash','active','now','now',?)",
                (expires_at,),
            )
            if candidate:
                conn.execute(
                    "INSERT INTO workflow_child_result_candidates(id,child_execution_id,parent_claim_id,kind,payload_json,artifact_refs_json,state,created_at) "
                    "VALUES('CANDIDATE','CHILD',?,'candidate_patch','{\"summary\":\"kept\"}','[\"patch:1\"]','collected','now')",
                    (self.claim_id,),
                )
        self.mutate(seed)

    def test_active_local_child_refuses_scope_reclamation(self) -> None:
        self.seed_dispatch()
        self.seed_child(expires_at="2999-01-01T00:00:00Z")
        plan = self.engine().inspect("A")
        self.assertTrue(any(item["kind"] == "local_child" for item in plan["blockers"]))
        with self.assertRaises(TodoError):
            self.engine().execute(plan, "child is active")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM child_scope_leases WHERE child_execution_id='CHILD'").fetchone()[0], "active")

    def test_dead_local_child_is_terminalized_artifacts_preserved_and_parent_resumes(self) -> None:
        self.seed_dispatch()
        self.seed_child(expires_at="2000-01-01T00:00:00Z")
        engine = self.engine()
        plan = engine.inspect("A")
        child_action = next(item for item in plan["actions"] if item["kind"] == "terminalize_dead_child")
        self.assertEqual(child_action["preserved_candidate_ids"], ["CANDIDATE"])
        result = engine.execute(plan, "dead subordinate")
        self.assertEqual(result["resume"], "next_task")
        with self.repo.service.db.read() as conn:
            execution = conn.execute("SELECT state FROM child_executions WHERE id='CHILD'").fetchone()[0]
            attempt = conn.execute("SELECT state FROM child_attempts WHERE id='ATTEMPT'").fetchone()[0]
            lease = conn.execute("SELECT state FROM child_scope_leases WHERE child_execution_id='CHILD'").fetchone()[0]
            candidate = conn.execute("SELECT state,payload_json,artifact_refs_json FROM workflow_child_result_candidates WHERE id='CANDIDATE'").fetchone()
            parent_lane_membership = conn.execute("SELECT COUNT(*) FROM workflow_lane_tasks WHERE task_id='A'").fetchone()[0]
            child_lane_membership = conn.execute(
                "SELECT COUNT(*) FROM workflow_lane_tasks lt JOIN child_executions c ON c.id=lt.task_id WHERE c.id='CHILD'"
            ).fetchone()[0]
        self.assertEqual((execution, attempt, lease), ("failed", "failed", "released"))
        self.assertEqual(candidate["state"], "collected")
        self.assertIn("patch:1", candidate["artifact_refs_json"])
        self.assertEqual(parent_lane_membership, 1)  # v2 plans normalize to one serial compatibility lane.
        self.assertEqual(child_lane_membership, 0)

    def test_supervisor_status_overrides_child_lease_age_safely(self) -> None:
        self.seed_dispatch()
        self.seed_child(expires_at="2999-01-01T00:00:00Z")
        stopped = RecoveryEngine(
            self.repo.service.db, self.repo.root, self.project_uuid,
            process_probe=lambda h, p, s: False,
            child_process_probe=lambda child: False,
        )
        self.assertTrue(any(item["kind"] == "terminalize_dead_child" for item in stopped.inspect("A")["actions"]))
        live = RecoveryEngine(
            self.repo.service.db, self.repo.root, self.project_uuid,
            process_probe=lambda h, p, s: False,
            child_process_probe=lambda child: True,
        )
        self.assertTrue(any(item.get("state") == "demonstrably_live" for item in live.inspect("A")["blockers"]))

    def test_running_gate_and_background_resource_refuse_recovery(self) -> None:
        self.seed_dispatch()
        def seed(conn, revision):
            conn.execute("UPDATE gates SET status='running' WHERE task_id='A'")
            conn.execute("INSERT INTO gates(id,task_id,type,status,valid) VALUES('ACTIVE-GATE','A','command','running',0)")
            conn.execute("INSERT INTO resource_classes(id,mode,metadata_json) VALUES('gpu','exclusive','{}')")
            conn.execute("INSERT INTO resource_instances(id,class_id,capacity,hostname,metadata_json) VALUES('gpu:0','gpu',1,?,'{}')", (socket.gethostname(),))
            conn.execute(
                "INSERT INTO resource_leases(id,instance_id,session_id,token_hash,state,hostname,pid,acquired_at,heartbeat_at,expires_at,command_json) "
                "VALUES('GPU-LEASE','gpu:0',?,'resource-hash','active',?,?,'now','now','2999-01-01T00:00:00Z','[\"cuda-campaign\"]')",
                (self.session_id, socket.gethostname(), os.getpid()),
            )
        self.mutate(seed)
        plan = self.engine(lambda h, p, s: p == os.getpid()).inspect("A")
        kinds = {item["kind"] for item in plan["blockers"]}
        self.assertTrue({"gate", "resource"} <= kinds)

    def test_stale_lock_and_resource_are_released(self) -> None:
        self.seed_dispatch()
        def seed(conn, revision):
            conn.execute("INSERT INTO named_locks(name,capacity,metadata_json) VALUES('recovery-fixture',1,'{}')")
            conn.execute(
                "INSERT INTO lock_leases(id,lock_name,session_id,token_hash,state,acquired_at,heartbeat_at,expires_at,hostname,pid) "
                "VALUES('LOCK','recovery-fixture',?,'lock-hash','active','now','now','2000-01-01T00:00:00Z',?,999999)",
                (self.session_id, socket.gethostname()),
            )
            conn.execute("INSERT INTO resource_classes(id,mode,metadata_json) VALUES('cpu','exclusive','{}')")
            conn.execute("INSERT INTO resource_instances(id,class_id,capacity,hostname,metadata_json) VALUES('cpu:0','cpu',1,?,'{}')", (socket.gethostname(),))
            conn.execute(
                "INSERT INTO resource_leases(id,instance_id,session_id,token_hash,state,hostname,pid,acquired_at,heartbeat_at,expires_at) "
                "VALUES('RESOURCE','cpu:0',?,'resource-hash','active',?,999999,'now','now','2000-01-01T00:00:00Z')",
                (self.session_id, socket.gethostname()),
            )
        self.mutate(seed)
        engine = self.engine()
        plan = engine.inspect()
        kinds = {item["kind"] for item in plan["actions"]}
        self.assertTrue({"release_lock", "release_resource"} <= kinds)
        engine.execute(plan, "stale leases")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM lock_leases WHERE id='LOCK'").fetchone()[0], "recovered")
            self.assertEqual(conn.execute("SELECT state FROM resource_leases WHERE id='RESOURCE'").fetchone()[0], "recovered")

    def test_terminal_checkpoint_finalization_is_automatic_and_idempotent(self) -> None:
        token = self.repo.service.continue_work(task_id="T")["claim"]["claim_token"]
        self.repo.service.complete(token, "implemented")
        with self.repo.service.db.connect() as conn:
            conn.execute("UPDATE checkpoints SET state='pending',reached_at=NULL WHERE id='T-DONE'")
            conn.commit()
        engine = self.engine()
        plan = engine.inspect("T")
        self.assertTrue(any(item["kind"] == "finalize_terminal_checkpoints" for item in plan["actions"]))
        engine.execute(plan, "terminal reconciliation")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM checkpoints WHERE id='T-DONE'").fetchone()[0], "reached")
        self.assertTrue(engine.execute(engine.inspect("T"), "repeat")["idempotent_noop"])

    def test_interactive_single_confirmation_flow_has_no_approval_token(self) -> None:
        self.seed_dispatch()
        engine = self.engine()
        stdout = TtyBuffer()
        with self.assertRaises(TodoError) as mismatch:
            run_owner_recovery(
                engine, database_path=self.repo.service.paths.db_file, reason="owner request", task_id="A",
                stdin=TtyBuffer("wrong\n"), stdout=stdout,
            )
        self.assertEqual(mismatch.exception.code, "recovery_confirmation_mismatch")
        result = run_owner_recovery(
            engine, database_path=self.repo.service.paths.db_file, reason="owner request", task_id="A",
            stdin=TtyBuffer("A\n"), stdout=TtyBuffer(),
        )
        self.assertEqual(result["status"], "recovered")
        self.assertNotIn("approval_token", result)

    def test_tty_required_and_inspection_remains_read_only(self) -> None:
        self.seed_dispatch()
        before = self.repo.service.db.revision()
        plan = inspect_owner_recovery(self.engine(), "A")
        self.assertEqual(self.repo.service.db.revision(), before)
        self.assertEqual(plan["file_policy"], "preserve_all_no_repository_mutation")
        with self.assertRaises(TodoError) as error:
            run_owner_recovery(
                self.engine(), database_path=self.repo.service.paths.db_file, reason="noninteractive", task_id="A",
                stdin=io.StringIO("A\n"), stdout=io.StringIO(),
            )
        self.assertEqual(error.exception.code, "recovery_tty_required")

    def test_project_recovery_lock_serializes_owner_operations(self) -> None:
        path = self.repo.service.paths.db_file
        with project_recovery_lock(path):
            with self.assertRaises(TodoError) as error:
                with project_recovery_lock(path):
                    pass
        self.assertEqual(error.exception.code, "recovery_lock_busy")


if __name__ == "__main__":
    unittest.main()
