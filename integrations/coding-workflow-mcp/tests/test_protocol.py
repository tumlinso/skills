from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from coding_workflow_mcp.protocol import EXPECTED_TOOLS


class ProtocolTests(unittest.TestCase):
    def test_preserves_exact_six_workflow_contract_names(self) -> None:
        self.assertEqual(EXPECTED_TOOLS, {
            "next_task", "inspect_task", "coordinate_task", "delegate_task",
            "collect_delegation", "finish_task",
        })
        self.assertNotIn("recover_terminal_checkpoints", EXPECTED_TOOLS)
        self.assertNotIn("run_gates", EXPECTED_TOOLS)

    def test_installed_live_smoke_tracks_exact_v2_surface(self) -> None:
        package = Path(__file__).resolve().parents[1]
        smoke = (package / "scripts" / "live_two_readonly_smoke.py").read_text(encoding="utf-8")
        self.assertIn('"coordinate_task"', smoke)
        self.assertNotIn('"run_gates", "finish_task"', smoke)

    def test_local_worker_guidance_keeps_children_subordinate(self) -> None:
        package = Path(__file__).resolve().parents[1]
        skill = (package.parents[1] / "local-coding-worker" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("nonblocking subordinate child work", skill)
        self.assertNotIn("authorize independent,", skill)


if __name__ == "__main__":
    unittest.main()
