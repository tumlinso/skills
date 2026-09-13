from __future__ import annotations

import hashlib
import json
import unittest

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.models import TodoError


class RetirementTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        self.repo.apply(base_plan([safe_task("OLD", "src/old"), safe_task("KEEP", "src/keep"), safe_task("NEW", "src/new")]))
        def seed(conn, revision):
            for run, root in (("OLD-RUN", "OLD"), ("NEW-RUN", "NEW")):
                conn.execute("INSERT INTO workflow_runs(id,root_task_id,status,created_at,updated_at,revision) VALUES(?,?, 'active','now','now',?)", (run, root, revision))
            conn.execute("INSERT INTO workflow_lanes(id,run_id,role,created_at,updated_at,revision) VALUES('OLD-LANE','OLD-RUN','integrator','now','now',?)", (revision,))
            conn.execute("INSERT INTO workflow_lane_tasks(lane_id,position,task_id,state,enqueued_at,revision) VALUES('OLD-LANE',0,'OLD','queued','now',?)", (revision,))
        self.repo.service.db.mutate(actor_session_id=None, entity_type="fixture", entity_id="OLD", event_type="fixture.seed", payload={}, operation=seed)

    def tearDown(self) -> None:
        self.repo.close()

    def request(self):
        with self.repo.service.db.read() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id='OLD'").fetchone()
            fingerprint = hashlib.sha256(conn.serialize()).hexdigest()
        return {
            "source_run_id": "OLD-RUN", "successor_run_id": "NEW-RUN",
            "expected_project_uuid": self.repo.service.project["project_uuid"],
            "expected_revision": self.repo.service.db.revision(), "expected_fingerprint": fingerprint,
            "expected_tasks": {"OLD": {"status": row["status"], "version": row["version"], "revision": row["revision"],
                "row_digest": hashlib.sha256(json.dumps({field: row[field] for field in ("id", "parent_id", "kind", "title", "objective", "priority", "parallel_policy", "next_action", "notes", "status", "result", "revision", "completion_revision", "completion_commit") if field in row.keys()}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}},
            "dispositions": {"OLD": "superseded"}, "reason": "replace the obsolete run",
        }

    def test_exact_retirement_preserves_unrelated_history_and_is_idempotent(self):
        request = self.request()
        result = self.repo.service.retire_run_batch(request)
        self.assertEqual(result["status"], "retired")
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='OLD'").fetchone()[0], "superseded")
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='KEEP'").fetchone()[0], "planned")
            self.assertEqual(conn.execute("SELECT state FROM workflow_lane_tasks WHERE task_id='OLD'").fetchone()[0], "skipped")
            self.assertEqual(conn.execute("SELECT status FROM workflow_runs WHERE id='OLD-RUN'").fetchone()[0], "cancelled")
        revision = self.repo.service.db.revision()
        repeat = self.repo.service.retire_run_batch(request)
        self.assertEqual((repeat["status"], repeat["changed"], self.repo.service.db.revision()), ("already_retired", False, revision))

    def test_active_claim_and_external_consumer_are_rejected_without_partial_change(self):
        claim = self.repo.service.continue_work(task_id="OLD")
        request = self.request()
        with self.assertRaises(TodoError) as blocked:
            self.repo.service.retire_run_batch(request)
        self.assertEqual(blocked.exception.code, "retirement_not_quiescent")
        self.repo.service.release(claim["claim"]["claim_token"], "no_change_required", "fixture release")
        def consumer(conn, revision):
            conn.execute("INSERT INTO task_dependencies(task_id,type,prerequisite_task_id,condition_json) VALUES('KEEP','task','OLD','{}')")
        self.repo.service.db.mutate(actor_session_id=None, entity_type="fixture", entity_id="KEEP", event_type="fixture.consumer", payload={}, operation=consumer)
        request = self.request()
        with self.assertRaises(TodoError) as blocked:
            self.repo.service.retire_run_batch(request)
        self.assertEqual(blocked.exception.code, "retirement_external_consumers")
