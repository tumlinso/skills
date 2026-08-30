from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest import mock

SKILL_ROOT = Path(__file__).resolve().parents[1]
TODO_ROOT = SKILL_ROOT.parent / "todo-orchestrator"
for value in (str(SKILL_ROOT), str(TODO_ROOT)):
    if value not in sys.path:
        sys.path.insert(0, value)

from local_worker import canonical_runtime
from todo_orchestrator import runtime_identity


SKILLS_ROOT = SKILL_ROOT.parent


class CanonicalRuntimeBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_identity._reset_for_testing()

    def tearDown(self) -> None:
        runtime_identity._reset_for_testing()

    def test_bridge_uses_todo_identity_and_canonical_environment(self) -> None:
        with mock.patch.dict(os.environ, {
            "PROJECT_CONTROL_SKILLS_ROOT": str(SKILLS_ROOT),
        }, clear=True):
            identity, context = canonical_runtime.bind(SKILLS_ROOT)
            environment = canonical_runtime.subprocess_environment(identity)
        self.assertEqual(context["contract"], "PCU-RUNTIME-IDENTITY/1")
        self.assertEqual(environment["PROJECT_CONTROL_SKILLS_ROOT"], str(SKILLS_ROOT))

    def test_bridge_translates_identity_mismatch(self) -> None:
        mismatch = runtime_identity.RuntimeIdentityError("synthetic mismatch")
        with mock.patch.object(runtime_identity, "bind_canonical_runtime", side_effect=mismatch), \
                self.assertRaisesRegex(canonical_runtime.CanonicalRuntimeError, "runtime_identity_mismatch"):
            canonical_runtime.bind(SKILLS_ROOT)

    def test_bridge_rejects_conflicting_compatibility_variables(self) -> None:
        with mock.patch.dict(os.environ, {
            "PROJECT_CONTROL_SKILLS_ROOT": str(SKILLS_ROOT),
            "CODING_WORKFLOW_SKILLS_ROOT": str(SKILLS_ROOT.parent),
        }, clear=True), self.assertRaisesRegex(
            canonical_runtime.CanonicalRuntimeError, "runtime_identity_mismatch"
        ):
            canonical_runtime.bind(SKILLS_ROOT)


if __name__ == "__main__":
    unittest.main()
