from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from todo_common import (  # noqa: E402
    detect_resume_state,
    ensure_agents_md,
    ensure_root_files,
    ensure_workstream_file,
)


class ResumeLogicTests(unittest.TestCase):
    def test_detect_resume_state_finds_active_workstreams(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            ensure_root_files(repo_root)
            ensure_workstream_file(repo_root, "agent-alpha", "Alpha work", "in_progress", "alpha")
            ensure_workstream_file(repo_root, "agent-beta", "Beta work", "done", "beta")
            state = detect_resume_state(repo_root)
            self.assertTrue(state["has_root_todos"])
            self.assertEqual(len(state["active_workstreams"]), 1)
            self.assertEqual(state["active_workstreams"][0]["slug"], "agent-alpha")

    def test_agents_block_is_stable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            first = ensure_agents_md(repo_root)
            second = ensure_agents_md(repo_root)
            self.assertEqual(first, second)
            text = first.read_text(encoding="utf-8")
            self.assertEqual(text.count("todo-orchestrator:start"), 1)
            self.assertIn("consult `todos.md` first", text)


if __name__ == "__main__":
    unittest.main()
