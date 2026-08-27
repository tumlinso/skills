from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

from coding_workflow_mcp._canonical import canonical_server, protocol, skills_root


class CompatibilityShimTests(unittest.TestCase):
    def test_shim_loads_canonical_kernel_and_has_no_semantic_backend(self) -> None:
        root = PACKAGE.parents[1]
        with patch.dict(os.environ, {"CODING_WORKFLOW_SKILLS_ROOT": str(root)}):
            self.assertEqual(skills_root(), root)
            instance = protocol()
            self.assertEqual(type(instance).__module__, "todo_orchestrator.workflow.protocol")
            self.assertEqual(type(instance.port).__module__, "todo_orchestrator.workflow.service")
            self.assertEqual(canonical_server().name, "coding-workflow")
        for retired in ("backend.py", "handles.py", "normalize.py"):
            self.assertFalse((PACKAGE / "coding_workflow_mcp" / retired).exists())

    def test_import_has_no_repo_gpu_or_model_side_effects(self) -> None:
        with patch("subprocess.run", side_effect=AssertionError("startup subprocess")):
            __import__("coding_workflow_mcp.server")


if __name__ == "__main__":
    unittest.main()
