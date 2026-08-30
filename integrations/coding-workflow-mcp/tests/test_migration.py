from __future__ import annotations

from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp import migration


class MigrationForwardingTests(unittest.TestCase):
    def test_all_modes_forward_to_project_control(self) -> None:
        product = ModuleType("project_control.migration")
        product.MigrationError = ValueError  # type: ignore[attr-defined]
        calls: list[tuple[object, bool, bool]] = []
        product.migrate = (  # type: ignore[attr-defined]
            lambda repo, *, apply=False, remove=False:
            calls.append((repo, apply, remove)) or {"status": "dry_run"}
        )
        with patch.object(migration, "migration_api", return_value=product):
            self.assertEqual(migration.migrate("/repo"), {"status": "dry_run"})
            migration.migrate("/repo", apply=True)
            migration.migrate("/repo", apply=True, remove=True)
        self.assertEqual(calls, [
            ("/repo", False, False),
            ("/repo", True, False),
            ("/repo", True, True),
        ])

    def test_product_error_is_preserved_as_legacy_error_type(self) -> None:
        class ProductMigrationError(RuntimeError):
            pass

        product = ModuleType("project_control.migration")
        product.MigrationError = ProductMigrationError  # type: ignore[attr-defined]
        product.migrate = lambda *args, **kwargs: (_ for _ in ()).throw(  # type: ignore[attr-defined]
            ProductMigrationError("owned marker conflict")
        )
        with patch.object(migration, "migration_api", return_value=product):
            with self.assertRaisesRegex(migration.MigrationError, "owned marker conflict"):
                migration.migrate("/repo")

    def test_missing_product_is_a_bounded_legacy_error(self) -> None:
        with patch.object(
            migration, "migration_api",
            side_effect=migration.ProjectControlUnavailable("Project Control required"),
        ):
            with self.assertRaisesRegex(migration.MigrationError, "Project Control required"):
                migration.migrate("/repo")


if __name__ == "__main__":
    unittest.main()
