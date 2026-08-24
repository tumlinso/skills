from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.harnesses import CodexCliAdapter, QwenCodeAdapter
from local_worker.servers import LlamaCppServerAdapter
from local_worker.service import AdapterError, AdapterService, disposable_task_context


class FakeProcess:
    def __init__(self, argv, *, stdout_text="", returncode=0, **kwargs):
        self.argv = argv
        self.stdout_text = stdout_text
        self.returncode = None
        self.final_returncode = returncode
        self.terminated = False

    def poll(self):
        return self.returncode

    def communicate(self, timeout=None):
        self.returncode = self.final_returncode
        return self.stdout_text, ""

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        self.returncode = self.returncode if self.returncode is not None else 0
        return self.returncode


class ProcessFactory:
    def __init__(self, output=""):
        self.output = output
        self.processes = []

    def __call__(self, argv, **kwargs):
        process = FakeProcess(argv, stdout_text=self.output, **kwargs)
        self.processes.append(process)
        return process


class AdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.binary = self.root / "adapter-bin"
        self.binary.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        os.chmod(self.binary, 0o755)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_qwen_adapter_is_bounded_read_only_and_disposable(self) -> None:
        outcome = {
            "outcome": "completed", "summary": "reviewed", "changed_paths": [],
            "claims": [{"statement": "fixture reviewed", "evidence": [
                {"path": "adapter-bin", "line": 1, "end_line": 1},
            ]}],
            "risk": "low", "blocker": None,
        }
        output = json.dumps([{"type": "result", "is_error": False, "result": outcome,
                              "usage": {"input_tokens": 7}}])
        factory = ProcessFactory(output)
        adapter = QwenCodeAdapter(str(self.binary), process_factory=factory)
        handle = adapter.start({
            "cwd": str(self.root), "repository_root": str(self.root),
            "authorized_read_paths": ["adapter-bin"],
            "base_url": "http://127.0.0.1:8080/v1", "model": "local-fixture",
            "max_wall_time_seconds": 30, "max_tool_calls": 8,
        })
        result = adapter.run(handle, {"prompt": "Review the packet"})
        argv = factory.processes[0].argv
        self.assertEqual(result["model_outcome"]["summary"], "reviewed")
        self.assertIn("--bare", argv)
        self.assertNotIn("--safe-mode", argv)
        self.assertEqual(argv[argv.index("--openai-base-url") + 1], "http://127.0.0.1:8080/v1")
        self.assertIn("agent,shell,run_shell_command,write,edit,write_file", argv)
        self.assertEqual(adapter.usage(handle)["runs"], 1)
        self.assertFalse(adapter.cancel(handle)["canceled"])
        self.assertTrue(adapter.drain(handle)["draining"])
        with self.assertRaises(AdapterError):
            adapter.run(handle, {"prompt": "again"})
        self.assertTrue(adapter.evict(handle)["evicted"])
        self.assertEqual(adapter.health(handle)["state"], "evicted")

    def test_codex_adapter_is_ephemeral_json_read_only(self) -> None:
        output = "\n".join([
            json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
            json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}),
            json.dumps({"type": "turn.completed", "usage": {"input_tokens": 11, "output_tokens": 2}}),
        ])
        factory = ProcessFactory(output)
        adapter = CodexCliAdapter(str(self.binary), process_factory=factory)
        handle = adapter.start({"cwd": str(self.root), "config_overrides": ["model_provider=local"]})
        result = adapter.run(handle, {"prompt": "Explain the packet"})
        argv = factory.processes[0].argv
        self.assertEqual(result["text"], "done")
        self.assertIn("--ephemeral", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertIn("model_provider=local", argv)
        self.assertTrue(adapter.evict(handle)["evicted"])

    def test_llama_cpp_adapter_uses_health_and_chat_protocol_without_assets_install(self) -> None:
        model = self.root / "model.gguf"
        model.write_bytes(b"fixture-only")
        factory = ProcessFactory()
        calls = []

        def transport(method, url, payload, timeout):
            calls.append((method, url, payload))
            if url.endswith("/health"):
                return 200, {"status": "ok"}
            return 200, {"choices": [{"message": {"content": "answer"}}],
                         "usage": {"prompt_tokens": 3, "completion_tokens": 1}}

        adapter = LlamaCppServerAdapter(str(self.binary), process_factory=factory, transport=transport)
        handle = adapter.start({"model_path": str(model), "host": "127.0.0.1", "port": 18080})
        self.assertTrue(adapter.health(handle)["healthy"])
        result = adapter.run(handle, {"request_id": "r1", "messages": [{"role": "user", "content": "hi"}]})
        self.assertEqual(result["text"], "answer")
        self.assertTrue(calls[0][1].endswith("/health"))
        self.assertTrue(calls[1][1].endswith("/v1/chat/completions"))
        self.assertEqual(adapter.usage(handle)["completion_tokens"], 1)
        service = AdapterService()
        service.register("llama", adapter)
        self.assertTrue(service.cancel("llama", handle, "r2")["canceled"])
        self.assertTrue(adapter.drain(handle)["draining"])
        with self.assertRaises(AdapterError):
            adapter.run(handle, {"messages": [{"role": "user", "content": "again"}]})
        self.assertTrue(adapter.evict(handle)["evicted"])

    def test_service_routes_replaceable_adapters_and_context_is_removed(self) -> None:
        factory = ProcessFactory(json.dumps([{"type": "result", "is_error": False, "result": "ok"}]))
        adapter = QwenCodeAdapter(str(self.binary), process_factory=factory)
        service = AdapterService()
        service.register("qwen", adapter)
        self.assertTrue(service.inspect()["qwen"]["available"])
        with disposable_task_context() as context:
            path = context
            handle = service.start("qwen", {
                "cwd": str(self.root), "runtime_dir": str(context / "runtime"),
                "base_url": "http://127.0.0.1:8080/v1", "model": "local-fixture",
            })
            self.assertEqual(service.run("qwen", handle, {"prompt": "bounded"})["status"], "needs_codex")
            self.assertEqual(service.usage("qwen", handle)["runs"], 1)
            service.evict("qwen", handle)
        self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
