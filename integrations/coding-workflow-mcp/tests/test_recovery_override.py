from __future__ import annotations

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp import admin


class RecoveryCompatibilityTests(unittest.TestCase):
    def test_installed_admin_exposes_one_recover_command(self) -> None:
        arguments = ["recover", "--repo", "/repo", "--reason", "inspect", "--inspect-only"]
        with patch.object(admin, "run_admin", return_value=0) as forwarded:
            self.assertEqual(admin.main(arguments), 0)
        forwarded.assert_called_once_with(arguments)
        old = (PACKAGE / "scripts" / "recovery_admin.py").read_text(encoding="utf-8")
        self.assertNotIn("live-approve", old)
        self.assertNotIn("approval_token", old)

    def test_admin_contains_no_recovery_implementation(self) -> None:
        source = (PACKAGE / "coding_workflow_mcp" / "admin.py").read_text(encoding="utf-8")
        self.assertIn("run_admin", source)
        self.assertNotIn("RecoveryEngine", source)
        self.assertNotIn("todo_orchestrator", source)


if __name__ == "__main__":
    unittest.main()
