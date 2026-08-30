from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE))

class CapabilityCompatibilityTests(unittest.TestCase):
    def test_capabilities_resolve_to_hash_only_canonical_store(self) -> None:
        root = PACKAGE.parents[1]
        sys.path.insert(0, str(root / "todo-orchestrator"))
        from todo_orchestrator.workflow.capabilities import capability_hash

        handle = "wfc_" + "opaque-value"
        digest = capability_hash(handle)
        self.assertEqual(len(digest), 64)
        self.assertNotIn("opaque-value", digest)


if __name__ == "__main__":
    unittest.main()
