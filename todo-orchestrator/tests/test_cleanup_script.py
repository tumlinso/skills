from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "cleanup_todos.py"
INIT_SCRIPT = ROOT / "scripts" / "init_todos.py"
UPDATE_SCRIPT = ROOT / "scripts" / "update_todos.py"


class CleanupScriptTests(unittest.TestCase):
    def test_cleanup_refuses_when_any_workstream_is_unfinished(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--repo-root",
                    str(repo_root),
                    "--workstream",
                    "alpha",
                    "--objective",
                    "Alpha work",
                    "--status",
                    "in_progress",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo-root", str(repo_root), "--dry-run"],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Cleanup blocked", result.stdout)

    def test_cleanup_apply_deletes_completed_workstreams_and_compacts_ledgers(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--repo-root",
                    str(repo_root),
                    "--workstream",
                    "alpha",
                    "--objective",
                    "Alpha work",
                    "--status",
                    "done",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SCRIPT),
                    "--repo-root",
                    str(repo_root),
                    "--workstream",
                    "alpha",
                    "--status",
                    "done",
                    "--execution-state",
                    "closed",
                    "--progress-note",
                    "Alpha is complete",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--repo-root", str(repo_root), "--apply"],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Cleanup complete.", result.stdout)
            self.assertFalse((repo_root / "todos" / "alpha.md").exists())
            todos_text = (repo_root / "todos.md").read_text(encoding="utf-8")
            self.assertIn("_No active workstreams yet._", todos_text)
            self.assertIn("Ran `todo-cleanup`", todos_text)
            status_text = (repo_root / "todo-status.md").read_text(encoding="utf-8")
            self.assertIn("_No tracked workstreams yet._", status_text)
            self.assertIn("Safe to call `todo-cleanup`: yes", status_text)


if __name__ == "__main__":
    unittest.main()
