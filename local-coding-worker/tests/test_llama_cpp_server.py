from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.servers import LlamaCppServerAdapter


class FakeProcess:
    pid = 424242
    def __init__(self, argv, **kwargs):
        self.argv, self.kwargs, self.returncode = argv, kwargs, None
    def poll(self): return self.returncode
    def wait(self, timeout=None): self.returncode = 0; return 0
    def terminate(self): self.returncode = -15
    def kill(self): self.returncode = -9


class Factory:
    def __init__(self): self.processes = []
    def __call__(self, argv, **kwargs):
        process = FakeProcess(argv, **kwargs); self.processes.append(process); return process


class Help:
    stdout = "--ctx-size --n-gpu-layers --split-mode --tensor-split --main-gpu --cache-type-k --cache-type-v --numa --threads --fit"
    stderr = ""


class LlamaCppServerTests(unittest.TestCase):
    def test_v2_profile_passes_detected_flags_allocation_logs_and_health(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / "llama-server"; binary.write_text("#!/bin/sh\n"); binary.chmod(0o755)
            model = root / "model.gguf"; model.write_bytes(b"GGUFfixture")
            log = root / "server.log"
            factory = Factory(); help_calls = []
            def help_runner(*args, **kwargs): help_calls.append(args); return Help()
            def transport(method, *_args):
                if method == "POST":
                    return 200, {"choices": [{"finish_reason": "tool_calls", "message": {
                        "content": "{not-json", "role": "assistant", "reasoning_content": "plan",
                        "tool_calls": [{"id": "call-1", "type": "function", "function": {
                            "name": "search_source", "arguments": "{}"}}]}}],
                        "usage": {"completion_tokens": 9}}
                return 200, {"status": "ok"}
            adapter = LlamaCppServerAdapter(str(binary), process_factory=factory,
                help_runner=help_runner, transport=transport)
            profile = {"format": "CORE4-MODEL-SERVICE/2", "model_sha256": "a" * 64,
                "allocated_gpu_uuids": ["GPU-a", "GPU-b"], "split_mode": "layer",
                "tensor_split": [1, 2], "main_gpu": 0, "context_size": 16384,
                "kv_cache_type_k": "f16", "kv_cache_type_v": "f16", "fit": True,
                "cpu_threads": 8, "numa_policy": "distribute", "port": 18080,
                "log_path": str(log), "startup_timeout_seconds": 1, "idle_ttl_seconds": 30}
            handle = adapter.start({"model_path": str(model), "port": 18080, "service_profile": profile})
            process = factory.processes[0]
            self.assertEqual(process.kwargs["env"]["CUDA_VISIBLE_DEVICES"], "GPU-a,GPU-b")
            self.assertEqual(process.kwargs["env"]["GGML_CUDA_P2P"], "1")
            self.assertTrue(process.kwargs["start_new_session"])
            self.assertEqual(process.argv[process.argv.index("--tensor-split") + 1], "1,2")
            self.assertIn("--fit", process.argv)
            self.assertEqual(len(help_calls), 1)
            result = adapter.run(handle, {"messages": [{"role": "user", "content": "test"}]})
            metadata = result["response_metadata"]
            self.assertEqual((result["text"], metadata["finish_reason"]), ("{not-json", "tool_calls"))
            self.assertEqual(metadata["message"]["content_characters"], 9)
            self.assertEqual(metadata["message"]["tool_calls"]["type"], "array")
            self.assertEqual(metadata["message"]["reasoning_content"]["type"], "string")
            wide_profile = {**profile, "allocated_gpu_uuids": ["GPU-a", "GPU-b", "GPU-c", "GPU-d"],
                            "port": 18081, "log_path": str(root / "wide.log")}
            wide_handle = adapter.start({"model_path": str(model), "port": 18081,
                                         "service_profile": wide_profile})
            self.assertEqual(factory.processes[1].kwargs["env"]["CUDA_VISIBLE_DEVICES"],
                             "GPU-a,GPU-b,GPU-c,GPU-d")
            self.assertEqual(factory.processes[1].kwargs["env"]["GGML_CUDA_P2P"], "1")
            with mock.patch("os.killpg", side_effect=ProcessLookupError):
                adapter.evict(handle)
                adapter.evict(wide_handle)
            self.assertTrue(log.exists())
            self.assertTrue(adapter.quiescent(handle))


if __name__ == "__main__": unittest.main()
