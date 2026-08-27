from __future__ import annotations

from pathlib import Path
import unittest


class AgentClassBoundaryTests(unittest.TestCase):
    def test_child_execution_is_not_a_lane_or_rendezvous_participant(self) -> None:
        root = Path(__file__).resolve().parents[3]
        migration = (root / "todo-orchestrator" / "todo_orchestrator" / "migrations.py").read_text(encoding="utf-8")
        self.assertIn("workflow_rendezvous_participants", migration)
        participant_block = migration.split("CREATE TABLE IF NOT EXISTS workflow_rendezvous_participants", 1)[1].split(";", 1)[0]
        self.assertIn("REFERENCES workflow_lanes", participant_block)
        self.assertNotIn("child_execution", participant_block)


if __name__ == "__main__":
    unittest.main()
