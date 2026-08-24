from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.migration import END_MARKER, ROUTING_SECTION, START_MARKER, migrate


class MigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        self.original = """# Repository guidance

Use todo task IDs and gates as authority.
Run ctxpp for C++ context and retain CUDA and local-worker CLI fallback details.
"""
        (self.root / "AGENTS.md").write_text(self.original, encoding="utf-8")
        (self.root / "plan.json").write_text('{"task_id":"CE-ARCH-71"}\n', encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_dry_run_changes_nothing_and_classifies_existing_prose(self) -> None:
        result = migrate(self.root)
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual((self.root / "AGENTS.md").read_text(), self.original)
        self.assertIn("task plans", result["classification"]["preserve"])
        self.assertGreaterEqual(len(result["classification"]["fallback"]), 4)

    def test_apply_is_idempotent_and_preserves_active_plans(self) -> None:
        before_plan = (self.root / "plan.json").read_bytes()
        first = migrate(self.root, apply=True)
        first_content = (self.root / "AGENTS.md").read_text()
        second = migrate(self.root, apply=True)
        self.assertEqual(first["status"], "applied")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual((self.root / "AGENTS.md").read_text(), first_content)
        self.assertEqual(first_content.count(START_MARKER), 1)
        self.assertEqual(first_content.count(END_MARKER), 1)
        self.assertEqual((self.root / "plan.json").read_bytes(), before_plan)
        self.assertIn("Use todo task IDs and gates as authority.\n", first_content)
        self.assertIn("Run ctxpp for C++ context and retain CUDA and local-worker CLI fallback details.\n", first_content)

    def test_remove_deletes_only_marked_section(self) -> None:
        migrate(self.root, apply=True)
        result = migrate(self.root, apply=True, remove=True)
        content = (self.root / "AGENTS.md").read_text()
        self.assertEqual(result["status"], "applied")
        self.assertNotIn(START_MARKER, content)
        self.assertNotIn(END_MARKER, content)
        self.assertEqual(content, self.original)

    def test_script_emits_json_and_supports_dry_run(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "migrate.py"
        process = subprocess.run(
            [sys.executable, str(script), "--repo", str(self.root), "--dry-run"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True,
        )
        self.assertEqual(json.loads(process.stdout)["status"], "dry_run")


if __name__ == "__main__":
    unittest.main()
