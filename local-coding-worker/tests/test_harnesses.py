from __future__ import annotations

import json, os, tempfile, unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))
from local_worker.harnesses import QwenCodeAdapter


class HarnessTests(unittest.TestCase):
    def test_qwen_command_is_ephemeral_sandboxed_allowlisted_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); handle = adapter.start({"cwd": str(root), "runtime_dir": str(root / "runtime")})
            session = adapter._session(handle)
            argv, env = adapter.build_command(session, "bounded")
            self.assertIn("--safe-mode", argv); self.assertIn("--sandbox", argv)
            self.assertEqual(argv[argv.index("--approval-mode") + 1], "plan")
            self.assertEqual(argv[argv.index("--allowed-tools") + 1], "read_file,list_directory,glob,grep_search")
            self.assertNotIn("agent", argv[argv.index("--allowed-tools") + 1])
            self.assertEqual(argv[argv.index("--max-subagent-depth") + 1], "1")
            settings = json.loads((Path(env["QWEN_HOME"]) / "settings.json").read_text())
            self.assertTrue(settings["disableAllHooks"]); self.assertEqual(settings["mcpServers"], {})
            self.assertNotEqual(Path(env["QWEN_HOME"]), Path.home() / ".qwen")

    def test_needs_codex_and_budget_are_normalized_successful_handoffs(self):
        adapter = QwenCodeAdapter("qwen")
        self.assertEqual(adapter.normalize_outcome("NEEDS_CODEX", {"core4": {}})["outcome"], "NEEDS_CODEX")
        budget = adapter.normalize_outcome("", {"core4": {"budget_exhausted": True}})
        self.assertEqual((budget["status"], budget["outcome"]), ("needs_codex", "NEEDS_CODEX"))

if __name__ == "__main__": unittest.main()
