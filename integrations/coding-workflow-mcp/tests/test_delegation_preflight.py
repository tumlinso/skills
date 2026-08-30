from __future__ import annotations

from pathlib import Path
import sys
import unittest

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

class DelegationCompatibilityTests(unittest.TestCase):
    def test_local_worker_remains_subordinate_adapter_not_backend(self) -> None:
        root = PACKAGE.parents[1]
        canonical = (root / "todo-orchestrator" / "todo_orchestrator" / "workflow" / "service.py").read_text(encoding="utf-8")
        child_skill = (root / "local-coding-worker" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("compose_child_packet", canonical)
        self.assertIn("parent claim", child_skill)
        self.assertFalse((PACKAGE / "coding_workflow_mcp" / "backend.py").exists())


if __name__ == "__main__":
    unittest.main()
