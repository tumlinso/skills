from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from v2_helpers import V2Repo  # noqa: F401 - establishes the package test path

from todo_orchestrator.config import utc_now
from todo_orchestrator.db import Database
from todo_orchestrator.models import TodoError
from todo_orchestrator.workflow.context_fragments import (
    ContextFragmentStore,
    FragmentOwner,
    compose_child_packet,
    compose_legacy_capsule,
)
from todo_orchestrator.workflow.foundation import canonical_json


class WorkflowContextFragmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.temporary.name) / "state.sqlite3")
        self.db.initialize({"project_uuid": "project-1", "project_name": "fixture"})
        now = utc_now()

        def seed(conn, revision):
            for task_id in ("ROOT", "TASK-1", "TASK-2"):
                conn.execute(
                    "INSERT INTO tasks(id,kind,title,status,created_at,updated_at,revision) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (task_id, "task", task_id, "planned", now, now, revision),
                )
            conn.execute(
                "INSERT INTO workflow_runs(id,root_task_id,created_at,updated_at,revision) VALUES(?,?,?,?,?)",
                ("run-1", "ROOT", now, now, revision),
            )
            conn.execute(
                "INSERT INTO workflow_lanes(id,run_id,role,created_at,updated_at,revision) VALUES(?,?,?,?,?,?)",
                ("lane-1", "run-1", "implementer", now, now, revision),
            )
            conn.execute(
                "INSERT INTO workflow_lanes(id,run_id,parent_lane_id,role,created_at,updated_at,revision) "
                "VALUES(?,?,?,?,?,?,?)",
                ("lane-2", "run-1", "lane-1", "validator", now, now, revision),
            )
            conn.executemany(
                "INSERT INTO workflow_lane_tasks(lane_id,position,task_id,state,enqueued_at,revision) "
                "VALUES(?,?,?,'queued',?,?)",
                [("lane-1", 0, "TASK-1", now, revision), ("lane-2", 0, "TASK-2", now, revision)],
            )

        self.db.mutate(
            actor_session_id=None,
            entity_type="fixture",
            entity_id="run-1",
            event_type="fixture_seeded",
            payload={},
            operation=seed,
        )
        self.store = ContextFragmentStore(self.db)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def publish(self, kind, content, *, lane_id=None, task_id=None, invalidate=()):
        return self.store.publish(
            actor_session_id=None,
            owner=FragmentOwner("run-1", lane_id, task_id),
            kind=kind,
            content=content,
            invalidate_fragment_ids=invalidate,
        )[0]

    def test_versions_and_hashes_are_stable_and_supersession_is_revisioned(self) -> None:
        content = {"objective": "Build the workflow", "invariants": ["children are subordinate"]}
        first = self.publish("run_charter", content)
        duplicate = self.publish("run_charter", dict(reversed(list(content.items()))))
        self.assertEqual(first.id, duplicate.id)
        self.assertEqual(first.version, 1)
        self.assertEqual(first.content_hash, duplicate.content_hash)

        second = self.publish("run_charter", {**content, "objective": "Build protocol v2"})
        self.assertEqual(second.version, 2)
        old = self.store.get(first.id)
        self.assertFalse(old.active)
        self.assertEqual(old.superseded_by, second.id)
        self.assertGreater(old.invalidation_revision, old.creation_revision)

    def test_targeted_invalidation_does_not_stale_unrelated_fragments(self) -> None:
        lane = self.publish("lane_brief", {"role": "implementer"}, lane_id="lane-1")
        task = self.publish("task_brief", {"objective": "old"}, lane_id="lane-1", task_id="TASK-1")
        decision = self.publish(
            "decision_ledger",
            {"decisions": [{"id": "D-1", "value": "new"}]},
            invalidate=(task.id,),
        )
        self.assertTrue(self.store.get(lane.id).active)
        self.assertFalse(self.store.get(task.id).active)
        self.assertTrue(decision.active)
        stale = self.store.compose_first_class(
            run_id="run-1",
            lane_id="lane-1",
            task_id="TASK-1",
            known_manifest={lane.id: lane.version, task.id: task.version, decision.id: decision.version},
        )
        self.assertEqual(stale["status"], "context_stale")
        changed = {item["fragment_id"]: item for item in stale["changed_fragments"]}
        self.assertTrue(changed[task.id]["invalidated"])
        self.assertNotIn(lane.id, changed)

    def test_compact_capsule_manifest_and_targeted_context_stale(self) -> None:
        charter = self.publish(
            "run_charter",
            {"objective": "Parallel project", "invariants": ["serial lanes"], "internal_notes": "expand only"},
        )
        lane = self.publish(
            "lane_brief",
            {"role": "implementer", "ordered_tasks": ["TASK-1"], "sibling_transcript": "not replayed"},
            lane_id="lane-1",
        )
        task = self.publish(
            "task_brief",
            {"objective": "Implement", "scope": ["src/a.py"], "forbidden_mutations": ["src/b.py"]},
            lane_id="lane-1",
            task_id="TASK-1",
        )
        delta = self.publish(
            "delta_inbox",
            {"cursor": 4, "messages": [{"kind": "status", "summary": "ready"}]},
            lane_id="lane-1",
        )
        known = {item.id: item.version for item in (charter, lane, task, delta)}
        current = self.store.compose_first_class(
            run_id="run-1", lane_id="lane-1", task_id="TASK-1", known_manifest=known
        )
        self.assertEqual(current["status"], "current")
        self.assertLessEqual(len(canonical_json(current).encode()), 8 * 1024)
        self.assertNotIn("internal_notes", current["run_summary"])
        self.assertNotIn("sibling_transcript", current["lane_brief"])

        revised = self.publish(
            "task_brief",
            {"objective": "Implement revised contract", "scope": ["src/a.py"]},
            lane_id="lane-1",
            task_id="TASK-1",
        )
        stale = self.store.compose_first_class(
            run_id="run-1", lane_id="lane-1", task_id="TASK-1", known_manifest=known
        )
        self.assertEqual(stale["status"], "context_stale")
        changed = {item["fragment_id"]: item for item in stale["changed_fragments"]}
        self.assertEqual(set(changed), {task.id, revised.id})
        self.assertTrue(changed[task.id]["invalidated"])
        self.assertFalse(changed[revised.id]["invalidated"])

    def test_delta_is_lane_specific(self) -> None:
        self.publish("delta_inbox", {"cursor": 1, "messages": ["lane one"]}, lane_id="lane-1")
        self.publish("delta_inbox", {"cursor": 9, "messages": ["lane two"]}, lane_id="lane-2")
        capsule = self.store.compose_first_class(run_id="run-1", lane_id="lane-1", task_id="TASK-1")
        self.assertEqual(capsule["unread_delta"]["messages"], ["lane one"])

    def test_expansion_is_explicit_and_budgeted(self) -> None:
        fragment = self.publish("decision_ledger", {"decisions": [{"id": "D", "rationale": "x" * 500}]})
        expanded = self.store.expand(fragment.id, budget_bytes=2048)
        self.assertEqual(expanded["fragment"]["fragment_id"], fragment.id)
        with self.assertRaisesRegex(TodoError, "limit"):
            self.store.expand(fragment.id, budget_bytes=256)
        with self.assertRaisesRegex(TodoError, "256..65536"):
            self.store.expand(fragment.id, budget_bytes=128)

    def test_source_context_is_reference_only_and_secrets_are_rejected(self) -> None:
        fragment = self.publish(
            "source_packet_ref",
            {"references": [{"packet_id": "ctx-1", "content_hash": "abc", "target": "Widget", "paths": ["src/widget.py"]}]},
            lane_id="lane-1",
            task_id="TASK-1",
        )
        self.assertEqual(fragment.content["references"][0]["packet_id"], "ctx-1")
        with self.assertRaisesRegex(TodoError, "references"):
            self.publish(
                "source_packet_ref",
                {"references": [{"packet_id": "ctx-2", "content_hash": "def", "source": "whole tree"}]},
                lane_id="lane-1",
                task_id="TASK-1",
            )
        with self.assertRaisesRegex(TodoError, "forbidden"):
            self.publish("task_brief", {"objective": "x", "claim_token": "raw-secret"}, task_id="TASK-1")

    def test_legacy_v2_capsule_remains_bounded_without_secrets(self) -> None:
        result = compose_legacy_capsule(
            {"task": {"id": "OLD", "objective": "continue"}, "scope": {"exclusive_paths": ["a.py"]}}
        )
        self.assertEqual(result["compatibility_mode"], "legacy_v2_single_lane")
        self.assertLessEqual(len(canonical_json(result).encode()), 8 * 1024)
        with self.assertRaisesRegex(TodoError, "forbidden"):
            compose_legacy_capsule({"task": {"id": "OLD"}, "session_token": "secret"})

    def test_child_packet_is_narrow_allowlisted_and_under_four_kib(self) -> None:
        packet = compose_child_packet(
            delegated_objective="Measure one parser function",
            parent_constraints=["read only", "return candidate evidence"],
            parent_authorized_paths=["src"],
            child_authorized_paths=["src/parser.py"],
            source_packet_refs=[{"packet_id": "ctx-child", "content_hash": "123", "target": "parse", "paths": ["src/parser.py"]}],
            required_output_schema={"kind": "test_result", "fields": ["status", "summary"]},
            candidate_gates=["unit parser"],
            acceptance_gates=["parent suite"],
            interface_facts=[{"name": "parser-api", "version": "1"}],
        )
        self.assertEqual(packet["packet_class"], "subordinate_local_child")
        self.assertLessEqual(len(canonical_json(packet).encode()), 4 * 1024)
        for forbidden in (
            "run_charter",
            "lane_brief",
            "sibling_lanes",
            "messages",
            "decision_ledger",
            "rendezvous",
            "role",
            "task_claim",
        ):
            self.assertNotIn(forbidden, packet)

    def test_child_scope_is_strict_and_packet_rejects_raw_diagnostics(self) -> None:
        common = dict(
            delegated_objective="Inspect",
            parent_constraints=[],
            source_packet_refs=[{"packet_id": "ctx", "content_hash": "123", "paths": ["src/a.py"]}],
            required_output_schema={"kind": "source_finding"},
            candidate_gates=[],
            acceptance_gates=[],
        )
        with self.assertRaisesRegex(TodoError, "narrower"):
            compose_child_packet(
                **common,
                parent_authorized_paths=["src/a.py"],
                child_authorized_paths=["src/a.py"],
            )
        with self.assertRaisesRegex(TodoError, "subset"):
            compose_child_packet(
                **common,
                parent_authorized_paths=["src"],
                child_authorized_paths=["tests"],
            )
        with self.assertRaisesRegex(TodoError, "forbidden"):
            compose_child_packet(
                **common,
                parent_authorized_paths=["src"],
                child_authorized_paths=["src/a.py"],
                interface_facts=[{"name": "api", "stdout": "raw output"}],
            )

    def test_child_source_paths_are_within_minimal_child_scope(self) -> None:
        with self.assertRaises(TodoError) as broad:
            compose_child_packet(
                delegated_objective="Inspect parser",
                parent_constraints=["read only"],
                parent_authorized_paths=["src"],
                child_authorized_paths=["src/parser"],
                source_packet_refs=[{"packet_id": "ctx", "content_hash": "abc", "paths": ["src/other"]}],
                required_output_schema={"type": "object"},
                candidate_gates=[],
                acceptance_gates=[],
            )
        self.assertEqual(broad.exception.code, "child_scope_expansion")

    def test_fragment_owner_must_match_run_lane_and_task(self) -> None:
        with self.assertRaises(TodoError) as mismatch:
            self.publish("task_brief", {"objective": "wrong"}, lane_id="lane-2", task_id="TASK-1")
        self.assertEqual(mismatch.exception.code, "fragment_task_owner_mismatch")


if __name__ == "__main__":
    unittest.main()
