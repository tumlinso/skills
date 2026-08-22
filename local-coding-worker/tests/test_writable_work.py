from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
SKILLS = SKILL.parent
sys.path.insert(0, str(SKILL))
sys.path.insert(0, str(SKILLS / "todo-orchestrator"))

from local_worker.acceptance import (AcceptanceError, ScopeViolation, StaleSourceError,
                                     accept_patch_artifact, build_patch_artifact)
from local_worker.verification import require_verification
from local_worker.workspace import materialize_writable_workspace
from todo_orchestrator.runtime import capture_source_identity


def command(code: str) -> dict:
    return {"schema_version": 1, "argv": [sys.executable, "-c", code], "cwd": ".", "timeout_seconds": 20}


class WritableWorkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.email", "worker@example.invalid"], cwd=self.repo, check=True)
        subprocess.run(["git", "config", "user.name", "Worker Test"], cwd=self.repo, check=True)
        (self.repo / "src").mkdir()
        (self.repo / "docs").mkdir()
        (self.repo / "src/value.txt").write_text("base\n", encoding="utf-8")
        (self.repo / "docs/note.txt").write_text("note\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.repo, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.repo, check=True)
        self.artifacts = Path(self.temp.name) / "artifacts"

    def tearDown(self) -> None:
        self.temp.cleanup()

    def prepare_artifact(self, *, dirty_text: str = "base\n", worker_text: str = "worker\n"):
        (self.repo / "src/value.txt").write_text(dirty_text, encoding="utf-8")
        identity = capture_source_identity(self.repo)
        baseline = command(f"from pathlib import Path; assert Path('src/value.txt').read_text() == {dirty_text!r}")
        with materialize_writable_workspace(self.repo, identity, ["src"], [baseline]) as workspace:
            self.assertEqual((workspace.path / "src/value.txt").read_text(encoding="utf-8"), dirty_text)
            (workspace.path / "src/value.txt").write_text(worker_text, encoding="utf-8")
            (workspace.path / "src/new.txt").write_text("created\n", encoding="utf-8")
            external = require_verification(
                workspace.path,
                [command(f"from pathlib import Path; assert Path('src/value.txt').read_text() == {worker_text!r}; assert Path('src/new.txt').read_text() == 'created\\n'")],
                phase="external",
            )
            artifact = build_patch_artifact(workspace, self.artifacts, external)
        return identity, artifact

    def test_dirty_overlay_patch_acceptance_preserves_authority_and_runs_current_gate(self) -> None:
        identity, artifact = self.prepare_artifact(dirty_text="user baseline\n", worker_text="accepted\n")
        self.assertEqual(artifact["changed_paths"], ["src/new.txt", "src/value.txt"])
        result = accept_patch_artifact(
            self.repo,
            artifact,
            [command("from pathlib import Path; assert Path('src/value.txt').read_text() == 'accepted\\n'")],
        )
        self.assertTrue(result["accepted"])
        self.assertFalse(result["parent_task_completed"])
        self.assertEqual(result["source_identity_before"]["fingerprint"], identity["fingerprint"])
        self.assertEqual((self.repo / "src/value.txt").read_text(encoding="utf-8"), "accepted\n")
        self.assertEqual((self.repo / "src/new.txt").read_text(encoding="utf-8"), "created\n")

    def test_worker_change_outside_subset_scope_is_rejected(self) -> None:
        identity = capture_source_identity(self.repo)
        with materialize_writable_workspace(self.repo, identity, ["src"], [command("assert True")]) as workspace:
            (workspace.path / "docs/note.txt").write_text("forbidden\n", encoding="utf-8")
            external = require_verification(workspace.path, [command("assert True")], phase="external")
            with self.assertRaises(ScopeViolation):
                build_patch_artifact(workspace, self.artifacts, external)

    def test_stale_primary_is_rejected_before_patch_application(self) -> None:
        _, artifact = self.prepare_artifact(worker_text="candidate\n")
        (self.repo / "docs/note.txt").write_text("concurrent user change\n", encoding="utf-8")
        with self.assertRaises(StaleSourceError):
            accept_patch_artifact(self.repo, artifact, [command("assert True")])
        self.assertEqual((self.repo / "src/value.txt").read_text(encoding="utf-8"), "base\n")

    def test_failed_current_source_gate_reverses_patch(self) -> None:
        _, artifact = self.prepare_artifact(worker_text="candidate\n")
        with self.assertRaises(AcceptanceError):
            accept_patch_artifact(self.repo, artifact, [command("raise SystemExit(1)")])
        self.assertEqual((self.repo / "src/value.txt").read_text(encoding="utf-8"), "base\n")
        self.assertFalse((self.repo / "src/new.txt").exists())


if __name__ == "__main__":
    unittest.main()
