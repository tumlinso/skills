from __future__ import annotations

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp import runtime_identity


class RuntimeIdentityForwardingTests(unittest.TestCase):
    def test_legacy_variable_is_passed_to_canonical_todo_api(self) -> None:
        root = PACKAGE.parents[1]
        api = SimpleNamespace(locate_skills_root=lambda explicit: Path(explicit).resolve())
        with patch.object(runtime_identity, "_api", return_value=api), patch.dict(
            "os.environ", {"CODING_WORKFLOW_SKILLS_ROOT": str(root)}, clear=True,
        ):
            self.assertEqual(runtime_identity.locate_skills_root(), root.resolve())

    def test_bind_validate_and_context_are_only_forwarders(self) -> None:
        identity = object()
        calls: list[tuple[str, object]] = []
        api = SimpleNamespace(
            bind_canonical_runtime=lambda root: calls.append(("bind", root)) or identity,
            validate_runtime=lambda value: calls.append(("validate", value)),
            project_runtime_context=lambda repo, value: calls.append(("context", repo)) or {"repo": str(repo)},
        )
        root = PACKAGE.parents[1]
        with patch.object(runtime_identity, "_api", return_value=api), patch.dict(
            "os.environ", {"PROJECT_CONTROL_SKILLS_ROOT": str(root)}, clear=True,
        ):
            self.assertIs(runtime_identity.bind_canonical_runtime(), identity)
            runtime_identity.validate_runtime(identity)
            self.assertEqual(runtime_identity.project_runtime_context("/repo", identity), {"repo": "/repo"})
        self.assertEqual(calls[0], ("bind", root.resolve()))
        self.assertIn(("validate", identity), calls)

    def test_conflicting_root_aliases_fail_before_import(self) -> None:
        with patch.dict("os.environ", {
            "PROJECT_CONTROL_SKILLS_ROOT": "/one",
            "CODING_WORKFLOW_SKILLS_ROOT": "/two",
        }, clear=True):
            with self.assertRaisesRegex(RuntimeError, "runtime_identity_mismatch"):
                runtime_identity.locate_skills_root()

    def test_no_identity_or_fingerprint_implementation_is_copied(self) -> None:
        source = Path(runtime_identity.__file__).read_text(encoding="utf-8")
        self.assertNotIn("class RuntimeIdentity", source)
        self.assertNotIn("hashlib", source)
        self.assertNotIn("rglob", source)


if __name__ == "__main__":
    unittest.main()
