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
        with patch.object(sys, "argv", ["coding-workflow-admin", "--help"]):
            with self.assertRaises(SystemExit) as caught:
                admin.main()
        self.assertEqual(caught.exception.code, 0)
        old = (PACKAGE / "scripts" / "recovery_admin.py").read_text(encoding="utf-8")
        self.assertNotIn("live-approve", old)
        self.assertNotIn("approval_token", old)

    def test_admin_binds_canonical_runtime_before_todo_imports(self) -> None:
        source = (PACKAGE / "coding_workflow_mcp" / "admin.py").read_text(encoding="utf-8")
        self.assertIn("runtime_identity()", source)
        self.assertNotIn("skills_root()", source)


if __name__ == "__main__":
    unittest.main()
