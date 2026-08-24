from __future__ import annotations

import json, os, tempfile, unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))
from local_worker.harnesses import QwenCodeAdapter


class HarnessTests(unittest.TestCase):
    def test_qwen_command_is_ephemeral_provider_bound_allowlisted_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); handle = adapter.start({
                "cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4",
            })
            session = adapter._session(handle)
            argv, env = adapter.build_command(session, "bounded")
            self.assertIn("--bare", argv); self.assertNotIn("--safe-mode", argv); self.assertNotIn("--sandbox", argv)
            self.assertEqual(argv[argv.index("--auth-type") + 1], "openai")
            self.assertEqual(argv[argv.index("--openai-base-url") + 1], "http://127.0.0.1:8080/v1")
            self.assertEqual(argv[argv.index("--approval-mode") + 1], "plan")
            self.assertEqual(
                argv[argv.index("--allowed-tools") + 1],
                "read_file,list_directory,glob,grep_search,structured_output",
            )
            self.assertNotIn("agent", argv[argv.index("--allowed-tools") + 1])
            self.assertEqual(argv[argv.index("--max-subagent-depth") + 1], "1")
            self.assertEqual(argv[argv.index("--max-session-turns") + 1], "7")
            self.assertEqual(argv[argv.index("--max-tool-calls") + 1], "8")
            self.assertEqual(argv[argv.index("--max-wall-time") + 1], "180")
            self.assertTrue(argv[argv.index("--json-schema") + 1].startswith("@"))
            self.assertEqual(argv[argv.index("--model") + 1], "local-q4")
            settings = json.loads((Path(env["QWEN_HOME"]) / "settings.json").read_text())
            self.assertTrue(settings["disableAllHooks"]); self.assertEqual(settings["mcpServers"], {})
            self.assertEqual(settings["modelProviders"], {"openai": [{
                "baseUrl": "http://127.0.0.1:8080/v1", "envKey": "CORE4_LOCAL_API_KEY",
                "id": "local-q4", "name": "local-q4",
            }]})
            self.assertNotEqual(Path(env["QWEN_HOME"]), Path.home() / ".qwen")

    def test_budget_is_normalized_to_successful_handoff(self):
        adapter = QwenCodeAdapter("qwen")
        budget = adapter.normalize_outcome("", {"core4": {"budget_exhausted": True}})
        self.assertEqual((budget["status"], budget["outcome"]), ("needs_codex", "NEEDS_CODEX"))

if __name__ == "__main__": unittest.main()
