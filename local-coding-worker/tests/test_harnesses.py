from __future__ import annotations

import json, os, tempfile, unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))
from local_worker.harnesses import QwenCodeAdapter
from local_worker.service import AdapterError


class HarnessTests(unittest.TestCase):
    def test_qwen_command_is_ephemeral_provider_bound_allowlisted_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); adapter._core_tools_supported = True
            handle = adapter.start({
                "cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4",
            })
            session = adapter._session(handle)
            argv, env = adapter.build_command(session, "bounded")
            self.assertNotIn("--bare", argv); self.assertNotIn("--safe-mode", argv); self.assertNotIn("--sandbox", argv)
            self.assertEqual(argv[argv.index("--auth-type") + 1], "openai")
            self.assertEqual(argv[argv.index("--openai-base-url") + 1], "http://127.0.0.1:8080/v1")
            self.assertEqual(argv[argv.index("--approval-mode") + 1], "plan")
            self.assertEqual(
                argv[argv.index("--core-tools") + 1],
                "read_file,list_directory,glob,grep_search",
            )
            self.assertEqual(
                argv[argv.index("--allowed-tools") + 1],
                "read_file,list_directory,glob,grep_search",
            )
            self.assertNotIn("structured_output", argv[argv.index("--core-tools") + 1])
            self.assertNotIn("agent", argv[argv.index("--allowed-tools") + 1])
            self.assertEqual(argv[argv.index("--max-subagent-depth") + 1], "1")
            self.assertEqual(argv[argv.index("--max-session-turns") + 1], "9")
            self.assertEqual(argv[argv.index("--max-tool-calls") + 1], "9")
            self.assertEqual(argv[argv.index("--max-wall-time") + 1], "180")
            self.assertTrue(argv[argv.index("--json-schema") + 1].startswith("@"))
            self.assertEqual(argv[argv.index("--model") + 1], "local-q4")
            settings = json.loads((Path(env["QWEN_HOME"]) / "settings.json").read_text())
            self.assertTrue(settings["disableAllHooks"]); self.assertEqual(settings["mcpServers"], {})
            self.assertEqual(settings["context"]["fileName"], ".core4-no-project-context")
            self.assertEqual(settings["modelProviders"], {"openai": [{
                "baseUrl": "http://127.0.0.1:8080/v1", "envKey": "CORE4_LOCAL_API_KEY",
                "id": "local-q4", "name": "local-q4",
            }]})
            self.assertNotEqual(Path(env["QWEN_HOME"]), Path.home() / ".qwen")

    def test_readonly_caller_can_reduce_registered_core_tools(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); adapter._core_tools_supported = True
            handle = adapter.start({"cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4",
                "core_tools": ["read_file"], "allowed_tools": ["read_file"],
                "max_tool_calls": 6, "max_session_turns": 2})
            argv, _ = adapter.build_command(adapter._session(handle), "read once")
            self.assertEqual(argv[argv.index("--core-tools") + 1], "read_file")
            self.assertEqual(argv[argv.index("--allowed-tools") + 1], "read_file")
            self.assertEqual(argv[argv.index("--max-session-turns") + 1], "9")
            system_prompt = argv[argv.index("--system-prompt") + 1]
            self.assertIn("final action MUST be a call", system_prompt)
            self.assertIn("outcome=needs_codex", system_prompt)

    def test_empty_core_registry_uses_denied_real_anchor_and_no_approval_list(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); adapter._core_tools_supported = True
            handle = adapter.start({"cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4",
                "core_tools": [], "allowed_tools": [], "max_tool_calls": 0})
            argv, _ = adapter.build_command(adapter._session(handle), "terminal only")
            self.assertEqual(argv[argv.index("--core-tools") + 1], "read_file")
            self.assertNotIn("--allowed-tools", argv)
            self.assertNotIn("--bare", argv)
            self.assertIn("final action MUST be a call", argv[argv.index("--prompt") + 1])
            excluded = set(argv[argv.index("--exclude-tools") + 1].split(","))
            self.assertIn("read_file", excluded)
            self.assertIn("update_goal", excluded)
            self.assertIn("run_shell_command", excluded)
            self.assertIn("enter_worktree", excluded)
            self.assertIn("exit_worktree", excluded)
            self.assertNotIn("structured_output", excluded)

    def test_writable_registration_is_strict_and_bounded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary)); adapter._core_tools_supported = True
            handle = adapter.start({"cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4", "mode": "writable"})
            argv, _ = adapter.build_command(adapter._session(handle), "edit once")
            self.assertEqual(argv[argv.index("--core-tools") + 1],
                "read_file,list_directory,glob,grep_search,edit,write_file")
            self.assertEqual(argv[argv.index("--max-tool-calls") + 1], "11")
            self.assertEqual(argv[argv.index("--max-session-turns") + 1], "11")

    def test_missing_core_tools_support_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); binary = root / "qwen"
            binary.write_text("#!/bin/sh\necho 'Unknown arguments: core-tools, coreTools' >&2\nexit 1\n")
            binary.chmod(0o755)
            adapter = QwenCodeAdapter(str(binary))
            handle = adapter.start({"cwd": str(root), "runtime_dir": str(root / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-q4"})
            with self.assertRaisesRegex(AdapterError, "required --core-tools"):
                adapter.build_command(adapter._session(handle), "bounded")

    def test_exit_53_normalizes_to_nonretryable_needs_codex(self):
        adapter = QwenCodeAdapter("qwen"); adapter._core_tools_supported = True
        session = {"config": {}, "qwen_effective": {"core_tools": ["read_file"],
            "max_tool_calls": 6, "max_session_turns": 9}}
        outcome = adapter.normalize_process_error(53, "[]", "maximum turns", session)
        self.assertEqual(outcome["reason"], "harness_turn_limit")
        self.assertFalse(outcome["retryable"])
        self.assertEqual(outcome["diagnostic"]["exit_code"], 53)

    def test_budget_is_normalized_to_successful_handoff(self):
        adapter = QwenCodeAdapter("qwen")
        budget = adapter.normalize_outcome("", {"core4": {"budget_exhausted": True}})
        self.assertEqual((budget["status"], budget["outcome"]), ("needs_codex", "NEEDS_CODEX"))

if __name__ == "__main__": unittest.main()
