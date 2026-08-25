from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore, InvalidHandle


class OverrideBackend(CodingWorkflowBackend):
    def __init__(self, root: Path, store: CapabilityStore) -> None:
        self.root = root.resolve()
        self.store = store
        self.instance_id = "fi_restarted"
        self.active = True
        self.revision = 40
        self.override_calls = 0
        self.finish_calls = 0
        self.last_override_arguments: tuple[str, ...] = ()

    def canonical_repo(self, repo_root: str) -> Path:
        return self.root

    def todo(
        self, repo: Path, *arguments: str, allow_failure: bool = False,
        extra_env: dict[str, str] | None = None,
    ):
        command = arguments[0]
        if command == "bootstrap":
            return {"ok": True, "data": {
                "project_uuid": "project-override", "project_revision": self.revision
            }}
        if arguments[:2] == ("recover", "live-inspect"):
            return {"ok": True, "data": {
                "project_uuid": "project-override", "project_revision": self.revision,
                "task_id": "CE-ARCH-71", "claim_fingerprint": "a" * 64,
                "owner_system": "coding-workflow", "prior_instance_id": "fi_lost",
                "eligible": True, "blockers": [],
            }}
        if arguments[:2] == ("recover", "live-override"):
            self.override_calls += 1
            self.last_override_arguments = tuple(arguments)
            approval = (extra_env or {}).get("CODING_WORKFLOW_RECOVERY_APPROVAL")
            if approval != "toa_manual_secret":
                return {"ok": False, "code": "override_requires_permission"}
            if not self.active:
                return {"ok": False, "code": "approval_consumed"}
            self.active = False
            self.revision += 1
            return {"ok": True, "data": {
                "project_revision": self.revision,
                "claim": {
                    "claim_token": "toc_replacement_secret",
                    "claim_fingerprint": "b" * 64,
                    "retired_claim_fingerprint": "a" * 64,
                    "owner_instance_id": "fi_restarted",
                },
                "session": {"session_token": "tos_replacement_secret"},
                "task": {"id": "CE-ARCH-71", "title": "Recover", "objective": "Bounded",
                         "next_action": "finish"},
                "scope": {"exclusive_paths": ["src"], "read_paths": [], "forbidden_paths": []},
                "interlocks": [], "gates": [],
            }}
        if command == "pulse":
            return {"ok": True, "data": {"project_revision": self.revision}}
        if command == "complete":
            self.finish_calls += 1
            self.revision += 1
            return {"ok": True, "data": {"project_revision": self.revision}}
        if command == "continue":
            raise AssertionError("live claim override must not call ordinary continue")
        raise AssertionError(arguments)


class RecoveryOverrideTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.store = CapabilityStore(self.root / "state")
        self.backend = OverrideBackend(self.root, self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_permission_is_required_and_boolean_cannot_authorize(self) -> None:
        missing = self.backend.next_task(str(self.root), "CE-ARCH-71")
        self.assertEqual(missing["status"], "override_requires_permission")
        self.assertEqual(missing["claim_fingerprint"], "a" * 64)
        self.assertEqual(self.backend.override_calls, 0)

        boolean = self.backend.next_task(str(self.root), "CE-ARCH-71", True)  # type: ignore[arg-type]
        self.assertEqual(boolean["status"], "override_requires_permission")
        self.assertEqual(self.backend.override_calls, 0)

        forged = self.backend.next_task(str(self.root), "CE-ARCH-71", "toa_forged")
        self.assertEqual(forged["status"], "override_requires_permission")
        self.assertEqual(self.backend.override_calls, 1)
        self.assertTrue(self.backend.active)

    def test_admin_approval_refuses_noninteractive_creation(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "recovery_admin.py"
        result = subprocess.run(
            [sys.executable, str(script), "approve", "--repo", str(self.root),
             "--task-id", "CE-ARCH-71", "--reason", "model supplied"],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False, shell=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("interactive owner terminal", result.stderr)

    def test_approved_recovery_is_opaque_and_finish_removes_entire_lineage(self) -> None:
        recovered = self.backend.next_task(
            str(self.root), "CE-ARCH-71", "toa_manual_secret"
        )
        encoded = json.dumps(recovered, sort_keys=True).encode()
        self.assertEqual(recovered["status"], "claimed")
        self.assertTrue(recovered["manually_recovered"])
        self.assertNotIn(b"toc_replacement_secret", encoded)
        self.assertNotIn(b"tos_replacement_secret", encoded)
        self.assertNotIn(b"toa_manual_secret", encoded)
        self.assertNotIn("toa_manual_secret", self.backend.last_override_arguments)
        handle = recovered["workflow_handle"]
        replacement = self.store.get_workflow(handle)
        self.assertEqual(replacement["lineage_fingerprints"], ["a" * 64, "b" * 64])

        old_alias = self.store.create_workflow({
            "repo": str(self.root), "project_uuid": "project-override",
            "task_id": "CE-ARCH-71", "claim_token": "toc_retired_secret",
            "claim_fingerprint": "a" * 64, "lineage_fingerprints": ["a" * 64],
        })
        finished = self.backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(finished["status"], "finished")
        self.assertEqual(self.backend.finish_calls, 1)
        for alias in (handle, old_alias):
            with self.assertRaises(InvalidHandle):
                self.store.get_workflow(alias)


if __name__ == "__main__":
    unittest.main()
