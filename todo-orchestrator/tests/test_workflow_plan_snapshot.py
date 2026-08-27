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
