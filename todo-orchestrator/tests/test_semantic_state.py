from __future__ import annotations

import hashlib
import json
import subprocess
import unittest

from v2_helpers import V2Repo, base_plan, safe_task


class SemanticStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        tasks = [
            {
                "id": "CE-ARCH-00", "kind": "epic", "title": "CE architecture",
                "status": "done", "result": "validated", "parallel_policy": "serial",
            },
            safe_task(
                "CE-ARCH-92", "evidence/ce-arch", parent_id="CE-ARCH-00",
                status="done", result="validated",
                checkpoints=[{"id": "CE-ARCH-VALIDATED", "state": "reached"}],
                gates=[{"id": "CE-ARCH-92-GATE", "type": "manual", "accepted": True}],
                produced_artifacts=[{"kind": "validation", "path": "evidence/ce-arch/summary.json"}],
            ),
            safe_task(
                "CP-MATH-17", "src/old", status="superseded", result="superseded",
                objective="Superseded by CE-ARCH-60 after replacements validate.",
                checkpoints=[{"id": "CP-MATH-COMPLETE"}],
                gates=[{"id": "CP-MATH-OLD-GATE", "type": "manual", "accepted": False}],
            ),
            safe_task(
                "OLD-DONE", "src/older", status="done", result="validated",
                checkpoints=[{"id": "OLD-PENDING"}],
                gates=[{"id": "OLD-INVALID-GATE", "type": "manual", "accepted": False}],
            ),
            safe_task(
                "CURRENT", "src/current",
                depends_on=[{"type": "checkpoint", "checkpoint_id": "CP-MATH-COMPLETE"}],
            ),
        ]
        self.repo.apply(base_plan(tasks))
        with self.repo.service.db.connect() as conn:
            conn.execute("UPDATE gates SET status='passed',valid=1 WHERE id='CE-ARCH-92-GATE'")
            conn.commit()

    def tearDown(self) -> None:
        self.repo.close()

    def _state(self, *args: str) -> dict[str, object]:
        process, payload = self.repo.run("semantic", "state", *args)
        self.assertEqual(process.returncode, 0, payload)
        return payload["data"]

    def test_supersession_and_authoritative_readiness_are_normalized_once(self) -> None:
        data = self._state()
        tasks = {item["id"]: item for item in data["tasks"]}
        superseded = tasks["CP-MATH-17"]
        self.assertEqual(superseded["effective_state"], "superseded")
        self.assertTrue(superseded["terminal"])
        self.assertFalse(superseded["frontier_eligible"])
        self.assertFalse(superseded["attention_eligible"])
        self.assertIn("explicit_status_superseded", superseded["reason_codes"])
        self.assertEqual(tasks["CURRENT"]["effective_state"], "blocked")
        self.assertFalse(tasks["CURRENT"]["authoritative_ready"])

    def test_terminal_checkpoint_and_gate_state_is_filtered_unless_currently_required(self) -> None:
        data = self._state()
        checkpoints = {item["id"]: item for item in data["checkpoints"]}
        gates = {item["id"]: item for item in data["gates"]}
        self.assertEqual(checkpoints["OLD-PENDING"]["effective_state"], "historical_stale")
        self.assertFalse(checkpoints["OLD-PENDING"]["attention_eligible"])
        self.assertEqual(gates["OLD-INVALID-GATE"]["effective_state"], "historical_invalid")
        self.assertFalse(gates["OLD-INVALID-GATE"]["attention_eligible"])
        self.assertEqual(checkpoints["CP-MATH-COMPLETE"]["effective_state"], "inconsistent_current_dependency")
        self.assertTrue(checkpoints["CP-MATH-COMPLETE"]["attention_eligible"])
        codes = {item["code"] for item in data["contradictions"]}
        self.assertIn("current_dependency_on_stale_checkpoint", codes)

    def test_parent_hierarchy_defines_program_and_completed_program_summary(self) -> None:
        data = self._state("--program", "CE-ARCH-00")
        self.assertEqual({item["id"] for item in data["tasks"]}, {"CE-ARCH-00", "CE-ARCH-92"})
        program = next(item for item in data["programs"] if item["id"] == "CE-ARCH-00")
        self.assertEqual(program["basis"], "parent_hierarchy")
        self.assertTrue(program["complete"])

    def test_semantic_state_is_read_only_for_database_git_and_projections(self) -> None:
        snapshot = self.repo.root / ".todo-orchestrator" / "state.snapshot.json"
        projection = self.repo.root / "todos.md"
        before_files = (snapshot.read_bytes(), projection.read_bytes())
        before_git = subprocess.run(
            ["git", "-C", str(self.repo.root), "status", "--porcelain=v1", "--untracked-files=all"],
            capture_output=True, text=True, check=True,
        ).stdout
        with self.repo.service.db.read() as conn:
            before_revision = int(conn.execute("SELECT value FROM meta WHERE key='project_revision'").fetchone()[0])
            before_hash = hashlib.sha256(conn.serialize()).hexdigest()
        data = self._state("--current-only")
        with self.repo.service.db.read() as conn:
            after_revision = int(conn.execute("SELECT value FROM meta WHERE key='project_revision'").fetchone()[0])
            after_hash = hashlib.sha256(conn.serialize()).hexdigest()
        after_git = subprocess.run(
            ["git", "-C", str(self.repo.root), "status", "--porcelain=v1", "--untracked-files=all"],
            capture_output=True, text=True, check=True,
        ).stdout
        self.assertEqual((after_revision, after_hash), (before_revision, before_hash))
        self.assertEqual(data["read_authority_fingerprint"], before_hash)
        self.assertEqual((snapshot.read_bytes(), projection.read_bytes()), before_files)
        self.assertEqual(after_git, before_git)


if __name__ == "__main__":
    unittest.main()
