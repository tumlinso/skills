from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import EXPECTED_ENTRY_POINTS, CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore


def skills_root() -> Path:
    configured = os.environ.get("CODING_WORKFLOW_SKILLS_ROOT")
    return Path(configured).resolve() if configured else Path(__file__).resolve().parents[3]


class LivePublicContractTests(unittest.TestCase):
    def test_all_four_public_entry_points_remain_available(self) -> None:
        root = skills_root()
        for name, relative in EXPECTED_ENTRY_POINTS.items():
            with self.subTest(name=name):
                self.assertTrue((root / relative).is_file(), f"missing public entry point: {relative}")

    def test_backend_resolves_the_live_skills_root_without_startup_work(self) -> None:
        root = skills_root()
        with self.subTest(root=root):
            temporary = self.enterContext(__import__("tempfile").TemporaryDirectory())
            backend = CodingWorkflowBackend(store=CapabilityStore(Path(temporary) / "state"), skills_root=root)
            self.assertEqual(backend.skills_root, root)

    def test_local_worker_has_atomic_admission_before_child_contract(self) -> None:
        root = skills_root()
        worker = root / EXPECTED_ENTRY_POINTS["worker"]
        help_result = subprocess.run(
            [sys.executable, str(worker), "delegate", "--help"], cwd=root,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
        )
        help_text = help_result.stdout
        has_auto_mode = re.search(r"--mode\s+\{[^}]*\bauto\b[^}]*\}", help_text) is not None
        self.assertTrue(
            has_auto_mode,
            "missing public contract: local-worker delegate must atomically admit local capacity before "
            "creating a todo child or scope lease, expose mode=auto, and guarantee local_unavailable returns "
            "child_created=false and scope_locked=false",
        )

    def test_focused_local_worker_admission_suites_pass(self) -> None:
        root = skills_root()
        for pattern in ("test_supervisor.py", "test_production_integration.py", "test_core4_integration.py"):
            with self.subTest(pattern=pattern):
                result = subprocess.run(
                    [sys.executable, "-m", "unittest", "discover", "-s", "local-coding-worker/tests",
                     "-p", pattern, "-v"],
                    cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, shell=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr[-4000:])


if __name__ == "__main__":
    unittest.main()
