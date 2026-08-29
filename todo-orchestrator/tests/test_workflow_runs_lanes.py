from __future__ import annotations

import sqlite3
import unittest

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.claims import claim_best
from todo_orchestrator.graph import validate_acyclic
from todo_orchestrator.models import TodoError
from todo_orchestrator.sessions import create_session
from todo_orchestrator.workflow.lanes import (
    LaneService,
    advance_lane_in_transaction,
    dispatch_claim_in_transaction,
    wait_graph,
)
from todo_orchestrator.workflow.roles import allowed_actions, require_role_action
from todo_orchestrator.workflow.runs import RunService


class WorkflowRunsLanesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        self.repo.apply(base_plan([
            safe_task("T-ROOT", "root.txt", priority=1),
            safe_task("T-A1", "a1.txt", priority=20),
            safe_task("T-A2", "a2.txt", priority=10),
            safe_task("T-B1", "b1.txt", priority=30),
            safe_task("T-B2", "b2.txt", priority=5),
        ]))
        self.runs = RunService(self.repo.service.db)
        self.lanes = LaneService(self.repo.service.db)
        self.runs.create(run_id="RUN", charter={"objective": "parallel run", "invariants": ["children are subordinate"]})
        self.lanes.create(run_id="RUN", lane_id="ROOT", role="coordinator")
        self.lanes.create(run_id="RUN", lane_id="A", parent_lane_id="ROOT", role="implementer")
        self.lanes.create(run_id="RUN", lane_id="B", parent_lane_id="ROOT", role="validator")
        self.lanes.enqueue(lane_id="A", task_ids=["T-A1", "T-A2"])
        self.lanes.enqueue(lane_id="B", task_ids=["T-B1", "T-B2"])

    def tearDown(self) -> None:
        self.repo.close()

    def _claim(self, task_id: str) -> tuple[str, str]:
        credentials: dict[str, str] = {}

        def operation(conn, revision):
            session, session_token = create_session(conn, self.repo.root, {"test": True})
            claim, claim_token = claim_best(
                conn,
                self.repo.root,
                session["agent_id"],
                revision,
                7200,
                requested_task_id=task_id,
            )
            credentials["session_token"] = session_token
            credentials["claim_token"] = claim_token
            return {"session_id": session["agent_id"], "claim_id": claim["claim_id"]}

        result, _ = self.repo.service.db.mutate(
            actor_session_id=lambda value: value["session_id"],
            entity_type="claim",
            entity_id=lambda value: value["claim_id"],
            event_type="test.claimed",
            payload={"task_id": task_id},
            operation=operation,
        )
        self.assertTrue(credentials["claim_token"].startswith("toc_"))
        return result["session_id"], result["claim_id"]

    def test_run_charter_is_versioned_hashed_and_idempotent(self) -> None:
        duplicate = self.runs.create(run_id="RUN", charter={"objective": "parallel run", "invariants": ["children are subordinate"]})
        self.assertFalse(duplicate["created"])
        revised = self.runs.revise_charter(run_id="RUN", charter={"objective": "parallel run v2"})
        self.assertEqual(2, revised["charter_version"])
        inspected = self.runs.inspect("RUN")
        self.assertEqual("parallel run v2", inspected["charter"]["content"]["objective"])
        self.assertEqual(64, len(inspected["charter"]["content_hash"]))

    def test_lane_tree_and_server_side_role_enforcement(self) -> None:
        self.assertIn("fork", allowed_actions("coordinator"))
        self.assertNotIn("fork", allowed_actions("implementer"))
        with self.assertRaisesRegex(TodoError, "cannot perform") as denied:
            require_role_action("implementer", "fork")
        self.assertEqual("workflow_role_forbidden", denied.exception.code)
        with self.assertRaises(TodoError) as child:
            require_role_action("implementer", "claim_task", actor_kind="local_child")
        self.assertEqual("child_run_authority_forbidden", child.exception.code)
        changed = self.lanes.assign_role(actor_lane_id="ROOT", target_lane_id="B", role="specialist")
        self.assertTrue(changed["changed"])
        with self.assertRaises(TodoError) as self_assigned:
            self.lanes.assign_role(actor_lane_id="A", target_lane_id="A", role="coordinator")
        self.assertEqual("workflow_role_forbidden", self_assigned.exception.code)
        with self.assertRaises(TodoError) as second_root:
            self.lanes.create(run_id="RUN", lane_id="OTHER-ROOT", role="coordinator")
        self.assertEqual("workflow_root_lane_exists", second_root.exception.code)

    def test_assignment_is_deterministic_and_dependency_aware(self) -> None:
        candidates = self.lanes.candidates("RUN")
        self.assertEqual(["T-B1", "T-A1"], [item["task_id"] for item in candidates])
        self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="dependency",
            entity_id="T-B1",
            event_type="test.dependency.added",
            payload={},
            operation=lambda conn, revision: conn.execute(
                "INSERT INTO task_dependencies(task_id,type,prerequisite_task_id,condition_json) VALUES('T-B1','task','T-A1','{}')"
            ).rowcount,
        )
        candidates = self.lanes.candidates("RUN")
        self.assertEqual(["T-A1"], [item["task_id"] for item in candidates])

    def test_each_lane_is_serial_while_different_lanes_dispatch_concurrently(self) -> None:
        session_a, claim_a = self._claim("T-A1")
        session_b, claim_b = self._claim("T-B1")
        dispatched_a = self.lanes.dispatch(run_id="RUN", session_id=session_a, claim_id=claim_a, context_version=1)
        dispatched_b = self.lanes.dispatch(run_id="RUN", session_id=session_b, claim_id=claim_b, context_version=1)
        self.assertEqual({"A", "B"}, {dispatched_a["lane_id"], dispatched_b["lane_id"]})
        resumed = self.lanes.dispatch(run_id="RUN", session_id=session_a, claim_id=claim_a, context_version=1)
        self.assertEqual("resumed", resumed["status"])
        with self.repo.service.db.read() as conn:
            active = conn.execute("SELECT lane_id,COUNT(*) AS n FROM workflow_dispatches WHERE state='active' GROUP BY lane_id ORDER BY lane_id").fetchall()
            lane_tasks = conn.execute("SELECT lane_id,COUNT(*) AS n FROM workflow_lane_tasks WHERE state='active' GROUP BY lane_id ORDER BY lane_id").fetchall()
        self.assertEqual([("A", 1), ("B", 1)], [(row["lane_id"], row["n"]) for row in active])
        self.assertEqual([("A", 1), ("B", 1)], [(row["lane_id"], row["n"]) for row in lane_tasks])

    def test_serial_policy_is_lane_local_in_first_class_run(self) -> None:
        self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="test",
            entity_id="serial-lanes",
            event_type="test.serial_lanes",
            payload={},
            operation=lambda conn, revision: conn.execute(
                "UPDATE tasks SET parallel_policy='serial',revision=? "
                "WHERE id IN ('T-A1','T-B1')",
                (revision,),
            ).rowcount,
        )
        self._claim("T-A1")
        self.assertEqual("ready", self.repo.service.explain("T-B1")["execution"])
        self._claim("T-B1")

    def test_serial_policy_remains_project_wide_without_distinct_lanes(self) -> None:
        self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="test",
            entity_id="legacy-serial",
            event_type="test.legacy_serial",
            payload={},
            operation=lambda conn, revision: (
                conn.execute(
                    "UPDATE tasks SET parallel_policy='serial',revision=? WHERE id='T-ROOT'",
                    (revision,),
                ),
                conn.execute(
                    "DELETE FROM workflow_lane_tasks WHERE task_id='T-ROOT'"
                ),
            )[0].rowcount,
        )
        self._claim("T-A1")
        self.assertEqual("blocked_scope", self.repo.service.explain("T-ROOT")["execution"])

    def test_database_constraints_reject_double_lane_dispatch(self) -> None:
        session_a, claim_a = self._claim("T-A1")
        self.lanes.dispatch(run_id="RUN", session_id=session_a, claim_id=claim_a, context_version=1)
        with self.repo.service.db.read() as read_conn:
            row = read_conn.execute("SELECT * FROM workflow_dispatches WHERE lane_id='A'").fetchone()
        with self.repo.service.db.connect() as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO workflow_dispatches(id,lane_id,session_id,claim_id,state,context_version,heartbeat_at,created_at,revision) "
                    "VALUES('duplicate','A',?,?, 'active',1,?,?,0)",
                    (session_a, claim_a, row["heartbeat_at"], row["created_at"]),
                )

    def test_managed_lane_cannot_dispatch_without_required_workspace(self) -> None:
        self.repo.service.db.mutate(
            actor_session_id=None, entity_type="lane", entity_id="A", event_type="test.workspace_required", payload={},
            operation=lambda conn, revision: conn.execute(
                "UPDATE workflow_lanes SET workspace_mode='isolated_merge',revision=? WHERE id='A'", (revision,)
            ),
        )
        session_id, claim_id = self._claim("T-A1")
        with self.assertRaises(TodoError) as caught:
            self.lanes.dispatch(run_id="RUN", session_id=session_id, claim_id=claim_id, context_version=1)
        self.assertEqual(caught.exception.code, "workflow_workspace_required")

    def test_stale_dispatch_is_attention_not_silent_reassignment(self) -> None:
        session_id, claim_id = self._claim("T-A1")
        dispatched = self.lanes.dispatch(run_id="RUN", session_id=session_id, claim_id=claim_id, context_version=1)
        result = self.lanes.reconcile_stale(stale_before="9999-01-01T00:00:00Z")
        self.assertEqual([dispatched["dispatch_id"]], [item["dispatch_id"] for item in result["stale_dispatches"]])
        with self.repo.service.db.read() as conn:
            self.assertEqual("stale", conn.execute("SELECT state FROM workflow_dispatches WHERE id=?", (dispatched["dispatch_id"],)).fetchone()[0])
            self.assertEqual("attention_required", conn.execute("SELECT state FROM workflow_lanes WHERE id='A'").fetchone()[0])
        self.assertNotIn("T-A1", [item["task_id"] for item in self.lanes.candidates("RUN")])

    def test_child_dispatch_rejection_and_parent_completion_authority(self) -> None:
        session_id, claim_id = self._claim("T-A1")
        self.repo.service.db.mutate(
            actor_session_id=session_id,
            entity_type="child_execution",
            entity_id="child-failed",
            event_type="test.child.failed",
            payload={"state": "failed"},
            operation=lambda conn, revision: conn.execute(
                "INSERT INTO child_executions(id,parent_claim_id,task_id,objective,state,max_attempts,attempt_count,result_json,created_at,completed_at) "
                "VALUES('child-failed',?,'T-A1','bounded check','failed',1,1,'{}','2026-01-01T00:00:00Z','2026-01-01T00:01:00Z')",
                (claim_id,),
            ).rowcount,
        )
        with self.assertRaises(TodoError) as rejected:
            self.repo.service.db.mutate(
                actor_session_id=None,
                entity_type="test",
                entity_id="child",
                event_type="test.child_dispatch",
                payload={},
                operation=lambda conn, revision: dispatch_claim_in_transaction(
                    conn, revision, run_id="RUN", session_id=session_id, claim_id=claim_id,
                    context_version=1, actor_kind="local_child",
                ),
            )
        self.assertEqual("child_lane_dispatch_forbidden", rejected.exception.code)
        dispatched = self.lanes.dispatch(run_id="RUN", session_id=session_id, claim_id=claim_id, context_version=1)
        with self.assertRaises(TodoError) as incomplete:
            self.repo.service.db.mutate(
                actor_session_id=session_id,
                entity_type="workflow_lane",
                entity_id="A",
                event_type="test.advance",
                payload={},
                operation=lambda conn, revision: advance_lane_in_transaction(
                    conn, revision, lane_id="A", task_id="T-A1", dispatch_id=dispatched["dispatch_id"]
                ),
            )
        self.assertEqual("workflow_parent_task_not_complete", incomplete.exception.code)
        with self.repo.service.db.read() as conn:
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM workflow_lanes WHERE id LIKE 'child%'").fetchone()[0])
            self.assertEqual("active", conn.execute("SELECT state FROM workflow_lane_tasks WHERE lane_id='A' AND task_id='T-A1'").fetchone()[0])
            self.assertEqual("in_progress", conn.execute("SELECT status FROM tasks WHERE id='T-A1'").fetchone()[0])

    def test_static_cycles_are_rejected_and_runtime_cycles_are_structured(self) -> None:
        with self.assertRaises(TodoError) as static:
            validate_acyclic([
                {"id": "X", "depends_on": [{"type": "task", "task_id": "Y"}]},
                {"id": "Y", "depends_on": [{"type": "task", "task_id": "X"}]},
            ])
        self.assertEqual("cyclic_graph", static.exception.code)

        def add_cycle(conn, revision):
            conn.execute("INSERT INTO task_dependencies(task_id,type,prerequisite_task_id,condition_json) VALUES('T-A1','task','T-B1','{}')")
            conn.execute("INSERT INTO task_dependencies(task_id,type,prerequisite_task_id,condition_json) VALUES('T-B1','task','T-A1','{}')")
            return {"cycle": True}

        self.repo.service.db.mutate(
            actor_session_id=None,
            entity_type="test",
            entity_id="cycle",
            event_type="test.runtime_cycle",
            payload={},
            operation=add_cycle,
        )
        with self.repo.service.db.read() as conn:
            report = wait_graph(conn, "RUN")
        self.assertEqual("attention_required", report["status"])
        self.assertIn({"nodes": ["task:T-A1", "task:T-B1"], "kind": "runtime_wait_cycle"}, report["cycles"])
        self.assertFalse(report["local_children_are_run_nodes"])


if __name__ == "__main__":
    unittest.main()
