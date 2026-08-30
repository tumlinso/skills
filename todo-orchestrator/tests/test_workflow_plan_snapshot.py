from __future__ import annotations

import unittest

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.projections import build_snapshot


class WorkflowPlanSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.repo = V2Repo()

    def tearDown(self):
        self.repo.close()

    def test_v2_plan_normalizes_to_one_serial_compatibility_lane(self):
        self.repo.apply(base_plan([safe_task("A", "src/a"), safe_task("B", "src/b")]))
        with self.repo.service.db.read() as conn:
            run = conn.execute("SELECT id,status FROM workflow_runs").fetchall()
            queue = conn.execute("SELECT lane_id,position,task_id FROM workflow_lane_tasks ORDER BY position").fetchall()
        self.assertEqual([tuple(row) for row in run], [("compat-v2", "active")])
        self.assertEqual([tuple(row) for row in queue], [("compat-v2-main", 0, "A"), ("compat-v2-main", 1, "B")])
        with self.repo.service.db.read() as conn:
            fragments = conn.execute(
                "SELECT kind,lane_id,task_id,owner_scope_json FROM workflow_context_fragments ORDER BY kind,task_id"
            ).fetchall()
        self.assertEqual({row["kind"] for row in fragments}, {"run_charter", "lane_brief", "task_brief"})
        self.assertTrue(all(row["owner_scope_json"] for row in fragments))

    def test_plan_reapply_never_downgrades_a_frozen_interface(self):
        contract = self.repo.root / "contracts" / "api.txt"
        contract.parent.mkdir(parents=True)
        contract.write_text("v1\n", encoding="utf-8")
        plan = base_plan(
            [safe_task("A", "contracts")],
            interfaces=[{"id": "API", "owner_task_id": "A", "contract_paths": ["contracts/api.txt"]}],
        )
        self.repo.apply(plan)
        capsule = self.repo.service.continue_work(task_id="A")
        self.repo.service.interface("freeze", "API", "1", capsule["claim"]["claim_token"])
        self.repo.apply(plan)
        status = self.repo.service.interface("status", "API")
        self.assertEqual((status["state"], status["version"]), ("frozen", "1"))
        self.assertTrue(status["content_hash"])

    def test_plan_reapply_accepts_unchanged_tasks_in_a_closed_lane(self):
        plan = base_plan([safe_task("A", "src/a")])
        self.repo.apply(plan)

        def close_lane(conn, revision):
            conn.execute("UPDATE workflow_lanes SET state='closed',revision=? WHERE id='compat-v2-main'", (revision,))
            conn.execute("UPDATE workflow_lane_tasks SET state='completed',revision=? WHERE lane_id='compat-v2-main'", (revision,))

        self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="fixture",
            entity_id="compat-v2-main",
            event_type="fixture.lane.closed",
            payload={},
            operation=close_lane,
        )
        self.repo.apply(plan)
        with self.repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT state FROM workflow_lanes WHERE id='compat-v2-main'").fetchone()[0], "closed")
            self.assertEqual(conn.execute("SELECT state FROM workflow_lane_tasks WHERE lane_id='compat-v2-main'").fetchone()[0], "completed")

    def test_explicit_v3_fragments_include_owner_scope(self):
        plan = base_plan([safe_task("A", "src/a")])
        plan["schema_version"] = 3
        plan["runs"] = [{
            "id": "RUN", "root_task_id": "A",
            "charter": {"objective": "bounded"},
            "lanes": [{"id": "ROOT", "role": "coordinator", "tasks": ["A"]}],
            "context_fragments": [{"kind": "decision_ledger", "content": {"decisions": []}}],
        }]
        self.repo.apply(plan)
        with self.repo.service.db.read() as conn:
            rows = conn.execute("SELECT kind,owner_scope_json FROM workflow_context_fragments WHERE run_id='RUN'").fetchall()
        self.assertIn("decision_ledger", {row["kind"] for row in rows})
        self.assertTrue(all(row["owner_scope_json"] for row in rows))

    def test_workflow_snapshot_is_deterministic_and_excludes_volatile_authority(self):
        self.repo.apply(base_plan([safe_task("A", "src/a")]))
        with self.repo.service.db.read() as conn:
            first = build_snapshot(conn, self.repo.service.project)
            second = build_snapshot(conn, self.repo.service.project)
        self.assertEqual(first, second)
        self.assertEqual(first["snapshot_version"], 3)
        names = set(first["tables"])
        self.assertIn("workflow_runs", names)
        self.assertIn("workflow_lanes", names)
        self.assertNotIn("workflow_capabilities", names)
        self.assertNotIn("workflow_dispatches", names)
        self.assertNotIn("workflow_child_result_candidates", names)


if __name__ == "__main__":
    unittest.main()
