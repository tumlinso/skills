from __future__ import annotations

from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp.protocol import EXPECTED_TOOLS


class GateCompatibilityTests(unittest.TestCase):
    def test_gate_execution_is_coordinate_action_not_discovered_tool(self) -> None:
        self.assertNotIn("run_gates", EXPECTED_TOOLS)
        source = (PACKAGE.parents[1] / "todo-orchestrator" / "todo_orchestrator" / "workflow" / "protocol.py").read_text(encoding="utf-8")
        self.assertIn('"run_gates":', source)
        self.assertIn('action == "run_gates"', (PACKAGE.parents[1] / "todo-orchestrator" / "todo_orchestrator" / "workflow" / "service.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
