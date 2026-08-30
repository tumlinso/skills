from __future__ import annotations

import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp import _canonical


class CompatibilityShimTests(unittest.TestCase):
    def test_shim_loads_canonical_kernel_and_has_no_semantic_backend(self) -> None:
        root = PACKAGE.parents[1]
        sys.path.insert(0, str(root / "todo-orchestrator"))
        identity = SimpleNamespace(
            package_source=root / "todo-orchestrator/todo_orchestrator/__init__.py",
            skills_root=root,
            package_root=root / "todo-orchestrator/todo_orchestrator",
            fingerprint="fixture",
        )
        with patch.object(_canonical, "runtime_identity", return_value=identity), patch.object(
            _canonical, "validate_runtime", return_value=None,
        ):
            instance = _canonical.protocol()
            self.assertEqual(type(instance).__module__, "todo_orchestrator.workflow.protocol")
            self.assertEqual(type(instance.port).__module__, "todo_orchestrator.workflow.service")
            self.assertEqual(_canonical.canonical_server().name, "coding-workflow")
        for retired in ("backend.py", "handles.py", "normalize.py"):
            self.assertFalse((PACKAGE / "coding_workflow_mcp" / retired).exists())

    def test_import_has_no_repo_gpu_or_model_side_effects(self) -> None:
        with patch("subprocess.run", side_effect=AssertionError("startup subprocess")):
            __import__("coding_workflow_mcp.server")


if __name__ == "__main__":
    unittest.main()
