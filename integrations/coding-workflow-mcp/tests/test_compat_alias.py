from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp import compat, migration


class CompatibilityAliasTests(unittest.TestCase):
    def test_codex_entry_forwards_exact_profile_arguments(self) -> None:
        cli = ModuleType("project_control.cli")
        calls: list[list[str]] = []
        cli.main = lambda argv: calls.append(argv) or 0  # type: ignore[attr-defined]
        cli._serve_profile = lambda *args, **kwargs: 0  # type: ignore[attr-defined]
        with patch.object(compat, "_project_control_module", return_value=cli):
            self.assertEqual(compat.run_codex(), 0)
        self.assertEqual(calls, [["serve", "codex"]])

    def test_admin_entry_forwards_arguments_without_interpreting_them(self) -> None:
        admin = ModuleType("project_control.admin")
        calls: list[list[str]] = []
        admin.main = lambda argv: calls.append(argv) or 0  # type: ignore[attr-defined]
        arguments = ["recover", "--repo", "/repo", "--reason", "owner", "--inspect-only"]
        with patch.object(compat, "_project_control_module", return_value=admin):
            self.assertEqual(compat.run_admin(arguments), 0)
        self.assertEqual(calls, [arguments])

    def test_internal_project_control_import_failure_does_not_fallback(self) -> None:
        error = ModuleNotFoundError("missing dependency", name="project_control_dependency")
        with patch.object(compat, "import_module", side_effect=error):
            with self.assertRaises(ModuleNotFoundError):
                compat.run_codex()

    def test_pre_pcu_project_control_uses_bounded_fallback(self) -> None:
        old_cli = ModuleType("project_control.cli")
        with patch.object(compat, "_project_control_module", return_value=old_cli), patch(
            "coding_workflow_mcp._canonical.run_fallback_server", return_value=0,
        ) as fallback:
            self.assertEqual(compat.run_codex(), 0)
        fallback.assert_called_once_with()

    def test_migration_is_forwarded_and_errors_remain_compatible(self) -> None:
        class ProductMigrationError(RuntimeError):
            pass

        product = ModuleType("project_control.migration")
        product.MigrationError = ProductMigrationError  # type: ignore[attr-defined]
        product.migrate = lambda repo, **kwargs: {"repo": repo, **kwargs}  # type: ignore[attr-defined]
        with patch.object(migration, "migration_api", return_value=product):
            self.assertEqual(
                migration.migrate("/repo", apply=True),
                {"repo": "/repo", "apply": True, "remove": False},
            )

    def test_package_has_no_independent_backend_or_migration_rules(self) -> None:
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted((PACKAGE / "coding_workflow_mcp").glob("*.py"))
            if path.name != "protocol.py"  # official-client compatibility smoke
        )
        self.assertNotIn("import sqlite3", sources)
        self.assertNotIn("class WorkflowKernel", sources)
        self.assertNotIn("workflow_front_door\"] =", sources)
        self.assertNotIn("ClientSession", sources)
        self.assertNotIn("stdio_client", sources)


if __name__ == "__main__":
    unittest.main()
