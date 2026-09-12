"""Independent, Git-object-only checks for the V01 donor review input."""
from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
BASELINE = "3652874793401944e3cde30a3134aeb5615316ba"
MAP = REPO / "docs/workflow_foundation_v2/validation/V01_DONOR_MAPPING.md"
EXPECTED_ROOT_ENTRIES = {
    "SKILL.md", "agents", "pyproject.toml", "references", "schemas", "scripts",
    "tests", "todo_orchestrator",
}
SENSITIVE_MARKERS = (".todo-orchestrator/", "state.snapshot", "capability_handle")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True)


class DonorMappingTest(unittest.TestCase):
    def test_frozen_donor_is_recoverable_and_every_root_entry_is_disposed(self) -> None:
        git("cat-file", "-e", f"{BASELINE}^{{commit}}")
        entries = {line.split("\t", 1)[1] for line in git(
            "ls-tree", f"{BASELINE}:todo-orchestrator").splitlines()}
        self.assertEqual(entries, EXPECTED_ROOT_ENTRIES)
        mapping = MAP.read_text(encoding="utf-8")
        for entry in entries:
            self.assertIn(f"`{entry}`", mapping)

    def test_review_boundary_excludes_sensitive_authority_state(self) -> None:
        mapping = MAP.read_text(encoding="utf-8")
        self.assertIn("Sensitive state is excluded", mapping)
        tracked = git("ls-tree", "-r", "--name-only", BASELINE, "--", "todo-orchestrator")
        for marker in SENSITIVE_MARKERS:
            self.assertNotIn(marker, tracked)
        self.assertIn("SQLite database", mapping)
        self.assertIn("authority token", mapping)

    def test_replacement_is_explicitly_deferred_until_parity_is_qualified(self) -> None:
        mapping = MAP.read_text(encoding="utf-8")
        self.assertIn("workflow_core", mapping)
        self.assertIn("qualified\nparity comparison", mapping)
        self.assertIn("frozen donor commit remains the fallback baseline", mapping)


if __name__ == "__main__":
    unittest.main()
