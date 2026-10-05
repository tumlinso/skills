from __future__ import annotations

import os
import json
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest import mock

SKILL = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(SKILL))

from local_worker.service import AdapterError
from local_worker.servers import LlamaCppServerAdapter
from local_worker.residency import process_identity


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
    stdout = "--ctx-size --n-gpu-layers --split-mode --tensor-split --main-gpu --cache-type-k --cache-type-v --numa --threads --fit --parallel --batch-size --ubatch-size --flash-attn"
    stderr = ""


class LlamaCppServerTests(unittest.TestCase):
    def _observer_adapter(self, transport, *, context_size=64):
        adapter = LlamaCppServerAdapter(transport=transport)
        adapter._servers["fixture"] = {"evicted": False, "accepting": True, "canceled": set(),
            "active_requests": set(), "base_url": "http://fixture", "profile": {"context_size": context_size},
            "reasoning_state": {}, "observer_generation": {}, "conservative_tokens_per_second": 10.0,
            "usage": {"runs": 0, "prompt_tokens": 0, "completion_tokens": 0, "duration_ms": 0}}
        return adapter

    def test_default_adapter_eviction_uses_actual_owned_pidfd_and_wait(self):
        process = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(90)'], start_new_session=True)
        try:
            with tempfile.TemporaryFile(mode='w+') as log:
                adapter = LlamaCppServerAdapter()
                adapter._servers['owned-cpu-fixture'] = {'process': process, 'accepting': True, 'evicted': False,
                    'termination_identity': process_identity(process.pid), 'log_stream': log}
                self.assertTrue(adapter.evict('owned-cpu-fixture')['evicted'])
                self.assertIsNotNone(process.poll())
                self.assertTrue(adapter.quiescent('owned-cpu-fixture'))
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=5)

    def test_spawn_ownership_callback_precedes_readiness_poll(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binary = root / 'llama-server'
            binary.write_text('#!/bin/sh\n')
            binary.chmod(0o755)
            model = root / 'fixture.gguf'
            model.write_bytes(b'GGUFfixture')
            order = []
            def transport(*args):
                order.append('health')
                self.assertEqual(order[0], 'owned')
                return 200, {}
            adapter = LlamaCppServerAdapter(str(binary), process_factory=Factory(),
                                           help_runner=lambda *a, **kw: Help(), transport=transport,
                                           identity_reader=lambda pid: {"pid": pid},
                                           owned_terminator=lambda identity: None)
            handle = adapter.start({'model_path': str(model), 'startup_timeout_seconds': 1,
                'on_spawn': lambda handle, info: order.append('owned')})
            self.assertEqual(order, ['owned', 'health'])
            adapter.evict(handle)

    def test_run_forwards_bounded_schema_and_validates_before_transport(self):
        calls = []
        def transport(*args):
            calls.append(args)
            return 200, {"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]}
        adapter = LlamaCppServerAdapter(transport=transport)
        adapter._servers["fixture"] = {"evicted": False, "accepting": True, "canceled": set(),
            "base_url": "http://fixture", "usage": {"runs": 0, "prompt_tokens": 0,
            "completion_tokens": 0, "duration_ms": 0}}
        schema = {"type": "object", "properties": {"summary": {"type": "string"}}}
        request = {"messages": [{"role": "user", "content": "packet"}],
            "response_format": {"type": "json_object", "schema": schema}, "temperature": 0}
        adapter.run("fixture", request)
        self.assertEqual(calls[0][2]["response_format"], request["response_format"])
        self.assertEqual(calls[0][2]["temperature"], 0)
        invalid_formats = [None, {"type": "json_schema", "schema": schema},
            {"type": "json_object", "schema": {"type": "array"}},
            {"type": "json_object", "schema": {"type": "object", "$ref": "file:///secret"}},
            {"type": "json_object", "schema": {"type": "object", "allOf": ({"$ref": "file:///secret"},)}},
            {"type": "json_object", "schema": {"type": "object", "description": "x" * 16384}}]
        for value in invalid_formats:
            with self.subTest(response_format=value), self.assertRaises(AdapterError):
                adapter.run("fixture", {**request, "response_format": value})
        for value in (True, -1, 3, float("nan"), float("inf"), "0"):
            with self.subTest(temperature=value), self.assertRaises(AdapterError):
                adapter.run("fixture", {**request, "temperature": value})
        self.assertEqual(len(calls), 1)

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
                if _args[0].endswith("/props"):
                    return 200, {"default_generation_settings": {"n_ctx": 4096}}
                return 200, {"status": "ok"}
            adapter = LlamaCppServerAdapter(str(binary), process_factory=factory,
                help_runner=help_runner, transport=transport,
                identity_reader=lambda pid: {"pid": pid}, owned_terminator=lambda identity: None)
            profile = {"format": "CORE4-MODEL-SERVICE/2", "model_sha256": "a" * 64,
                "allocated_gpu_uuids": ["GPU-a", "GPU-b"], "split_mode": "layer",
                "tensor_split": [1, 2], "main_gpu": 0, "context_size": 16384,
                "kv_cache_type_k": "f16", "kv_cache_type_v": "f16", "fit": True,
                "cpu_threads": 8, "numa_policy": "distribute", "port": 18080,
                "parallel_slots": 1, "batch_size": 512, "ubatch_size": 128, "flash_attention": "auto",
                "log_path": str(log), "startup_timeout_seconds": 1, "idle_ttl_seconds": 30}
            handle = adapter.start({"model_path": str(model), "port": 18080, "service_profile": profile})
            process = factory.processes[0]
            self.assertEqual(process.kwargs["env"]["CUDA_VISIBLE_DEVICES"], "GPU-a,GPU-b")
            self.assertEqual(process.kwargs["env"]["GGML_CUDA_P2P"], "1")
            self.assertTrue(process.kwargs["start_new_session"])
            self.assertEqual(process.argv[process.argv.index("--tensor-split") + 1], "1,2")
            self.assertEqual(process.argv[process.argv.index("--parallel") + 1], "1")
            self.assertEqual(process.argv[process.argv.index("--batch-size") + 1], "512")
            self.assertEqual(process.argv[process.argv.index("--ubatch-size") + 1], "128")
            self.assertEqual(process.argv[process.argv.index("--flash-attn") + 1], "auto")
            self.assertIn("--fit", process.argv)
            self.assertEqual(len(help_calls), 1)
            result = adapter.run(handle, {"messages": [{"role": "user", "content": "test"}]})
            metadata = result["response_metadata"]
            self.assertEqual((result["text"], metadata["finish_reason"]), ("{not-json", "tool_calls"))
            self.assertEqual(metadata["message"]["content_characters"], 9)
            self.assertEqual(metadata["message"]["tool_calls"]["type"], "array")
            self.assertEqual(metadata["message"]["reasoning_content"]["characters"], 4)
            self.assertNotIn("prefix", metadata["message"]["reasoning_content"])
            wide_profile = {**profile, "allocated_gpu_uuids": ["GPU-a", "GPU-b", "GPU-c", "GPU-d"],
                            "port": 18081, "log_path": str(root / "wide.log"),
                            "observer_generation": {"reasoning_tokens": 4096}}
            wide_handle = adapter.start({"model_path": str(model), "port": 18081,
                                         "service_profile": wide_profile})
            self.assertEqual(factory.processes[1].kwargs["env"]["CUDA_VISIBLE_DEVICES"],
                             "GPU-a,GPU-b,GPU-c,GPU-d")
            self.assertEqual(factory.processes[1].kwargs["env"]["GGML_CUDA_P2P"], "1")
            self.assertEqual(adapter._server(wide_handle)["effective_context_size"], 4096)
            with mock.patch("os.killpg", side_effect=ProcessLookupError):
                adapter.evict(handle)
                adapter.evict(wide_handle)
            self.assertTrue(log.exists())
            self.assertTrue(adapter.quiescent(handle))

    def test_observer_generation_uses_private_two_phase_completion_and_fixed_answer_budget(self):
        calls = []
        def transport(method, url, payload, timeout):
            calls.append((url.rsplit("/", 1)[-1], payload, timeout))
            if url.endswith("/apply-template"):
                thinking = payload["chat_template_kwargs"]["enable_thinking"]
                return 200, {"prompt": "SYS <think>" if thinking else "SYS <think></think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            if payload.get("stop") == ["</think>"]:
                return 200, {"content": "private thought", "tokens": [41, 42],
                    "timings": {"predicted_n": 2, "predicted_per_second": 20, "predicted_ms": 100,
                        "prompt_n": 1, "cache_n": 1}}
            return 200, {"content": "{}", "tokens": [43],
                "timings": {"predicted_n": 1, "predicted_per_second": 20, "predicted_ms": 50,
                    "prompt_n": 1, "cache_n": 4}}
        adapter = self._observer_adapter(transport)
        result = adapter.run("fixture", {"messages": [{"role": "user", "content": "question"}],
            "max_tokens": 16, "timeout_seconds": 60, "reasoning_mode": "auto",
            "reasoning_state_key": "lease-a", "observer_generation": {
                "reasoning_tokens": 128, "preserve_reasoning": True, "conservative_tokens_per_second": 10.0}})
        self.assertEqual(result["text"], "{}")
        self.assertEqual(result["usage"]["reasoning_tokens"], 2)
        self.assertEqual(result["usage"]["answer_tokens"], 1)
        self.assertEqual(result["usage"]["visible_tokens"], 1)
        self.assertEqual(result["usage"]["reasoning_prompt_tokens"], 2)
        self.assertEqual(result["usage"]["reasoning_prompt_evaluated_tokens"], 1)
        self.assertEqual(result["usage"]["reasoning_prompt_cached_tokens"], 1)
        self.assertEqual(result["usage"]["answer_prompt_tokens"], 5)
        self.assertEqual(result["usage"]["answer_prompt_evaluated_tokens"], 1)
        self.assertEqual(result["usage"]["answer_prompt_cached_tokens"], 4)
        self.assertEqual(result["usage"]["context_tokens"], 6)
        self.assertEqual([call[0] for call in calls], ["apply-template", "tokenize", "tokenize", "completion", "tokenize", "completion"])
        completions = [call[1] for call in calls if call[0] == "completion"]
        self.assertLessEqual(completions[0]["n_predict"], 128)
        self.assertEqual(completions[1]["n_predict"], 16)  # unused thought budget is not donated
        self.assertTrue(all(item["cache_prompt"] and item["id_slot"] == 0 for item in completions))
        self.assertNotIn("private thought", json.dumps(result["response_metadata"]))
        self.assertNotIn("private thought", json.dumps(result))

    def test_observer_reasoning_history_is_inquiry_local_and_clearable(self):
        rendered = []
        template_kwargs = []
        def transport(method, url, payload, timeout):
            if url.endswith("/apply-template"):
                rendered.append(payload["messages"])
                template_kwargs.append(payload["chat_template_kwargs"])
                return 200, {"prompt": "SYS <think>" if payload["chat_template_kwargs"]["enable_thinking"] else "SYS <think></think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            if payload.get("stop") == ["</think>"]:
                return 200, {"content": "private thought", "tokens": [41], "timings": {"predicted_n": 1, "predicted_per_second": 20}}
            return 200, {"content": "answer", "tokens": [42], "timings": {"predicted_n": 1, "predicted_per_second": 20}}
        adapter = self._observer_adapter(transport, context_size=256)
        policy = {"reasoning_tokens": 32, "preserve_reasoning": True, "conservative_tokens_per_second": 10.0}
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q1"}], "max_tokens": 16,
            "reasoning_state_key": "lease-a", "observer_generation": policy})
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q1"},
            {"role": "assistant", "content": "answer"}, {"role": "user", "content": "q2"}],
            "max_tokens": 16, "reasoning_state_key": "lease-a", "observer_generation": policy})
        self.assertIn("<think>private thought</think>answer", json.dumps(rendered[-1]))
        self.assertTrue(template_kwargs[-1]["preserve_thinking"])
        adapter.run("fixture", {"messages": [{"role": "user", "content": "another"}], "max_tokens": 16,
            "reasoning_state_key": "lease-b", "observer_generation": policy})
        self.assertNotIn("private thought", json.dumps(rendered[-1]))
        self.assertTrue(template_kwargs[-1]["preserve_thinking"])
        adapter.clear_reasoning("fixture", "lease-a")
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q1"},
            {"role": "assistant", "content": "answer"}, {"role": "user", "content": "q3"}],
            "max_tokens": 16, "reasoning_state_key": "lease-a", "observer_generation": policy})
        self.assertNotIn("<think>private thought</think>answer", json.dumps(rendered[-1]))

    def test_observer_context_shrinks_reasoning_before_rejecting_current_prompt(self):
        calls = []
        def transport(method, url, payload, timeout):
            calls.append((url.rsplit("/", 1)[-1], payload))
            if url.endswith("/apply-template"):
                return 200, {"prompt": "one two three <think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            if payload.get("stop") == ["</think>"]:
                return 200, {"content": "thought", "tokens": [41], "timings": {"predicted_n": 1, "predicted_per_second": 20}}
            return 200, {"content": "ok", "tokens": [42], "timings": {"predicted_n": 1, "predicted_per_second": 20}}
        adapter = self._observer_adapter(transport, context_size=24)
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 16,
            "reasoning_state_key": "lease-a", "observer_generation": {
                "reasoning_tokens": 128, "conservative_tokens_per_second": 10.0}})
        calls.clear()
        completion = adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 16,
            "reasoning_state_key": "lease-b", "observer_generation": {
                "reasoning_tokens": 128, "conservative_tokens_per_second": 10.0}})
        phase = [payload for endpoint, payload in calls if endpoint == "completion" and payload.get("stop")]
        self.assertEqual(len(phase), 1)
        self.assertLess(phase[0]["n_predict"], 128)
        self.assertEqual(completion["text"], "ok")

    def test_observer_output_byte_cap_fails_without_truncating(self):
        template_kwargs = []
        def transport(method, url, payload, timeout):
            if url.endswith("/apply-template"):
                template_kwargs.append(payload["chat_template_kwargs"])
                return 200, {"prompt": "SYS <think></think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            return 200, {"content": "é" * 8193, "tokens": [1], "timings": {"predicted_n": 1}}
        adapter = self._observer_adapter(transport)
        with self.assertRaisesRegex(AdapterError, "observer_visible_output_budget_exceeded"):
            adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 16,
                "reasoning_mode": "off", "reasoning_state_key": "lease-a",
                "observer_generation": {"preserve_reasoning": False}})
        self.assertFalse(template_kwargs[-1]["preserve_thinking"])

    def test_observer_answer_rejects_leaked_thinking_tags_without_returning_content(self):
        def transport(method, url, payload, timeout):
            if url.endswith("/apply-template"):
                return 200, {"prompt": "SYS <think></think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            return 200, {"content": "<think>private detail</think>{}", "tokens": [1], "timings": {"predicted_n": 1}}
        adapter = self._observer_adapter(transport)
        with self.assertRaisesRegex(AdapterError, "observer_visible_reasoning_output_rejected") as error:
            adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 16,
                "reasoning_mode": "off", "observer_generation": {"preserve_reasoning": False}})
        self.assertNotIn("private detail", str(error.exception))

    def test_observer_thinking_uses_only_measured_throughput_and_respects_short_turn_reserve(self):
        templates = []
        def transport(method, url, payload, timeout):
            if url.endswith("/apply-template"):
                templates.append(payload["chat_template_kwargs"]["enable_thinking"])
                return 200, {"prompt": "SYS <think>" if templates[-1] else "SYS <think></think>"}
            if url.endswith("/tokenize"):
                return 200, {"tokens": list(range(len(payload["content"].split())))}
            if payload.get("stop") == ["</think>"]:
                return 200, {"content": "thought", "tokens": [41], "timings": {"predicted_n": 1, "predicted_per_second": 20}}
            return 200, {"content": "x" * 32, "tokens": list(range(32)),
                "timings": {"predicted_n": 32, "predicted_per_second": 20}}
        adapter = self._observer_adapter(transport, context_size=4096)
        adapter._server("fixture")["conservative_tokens_per_second"] = None
        policy = {"reasoning_tokens": 64, "preserve_reasoning": False}
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 64,
            "timeout_seconds": 60, "reasoning_mode": "auto", "observer_generation": policy})
        self.assertEqual(templates, [False])  # no guessed throughput seed
        self.assertGreater(adapter._server("fixture")["conservative_tokens_per_second"], 0)
        measured = adapter._server("fixture")["conservative_tokens_per_second"]
        result = adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 64,
            "timeout_seconds": 60, "reasoning_mode": "auto",
            "observer_generation": {"reasoning_tokens": 1000, "preserve_reasoning": False,
                "conservative_tokens_per_second": 100.0}})
        self.assertEqual(templates[-1], True)
        self.assertLessEqual(result["usage"]["reasoning_token_budget"], int(44 * measured))
        adapter.run("fixture", {"messages": [{"role": "user", "content": "q"}], "max_tokens": 64,
            "timeout_seconds": 10, "reasoning_mode": "auto", "observer_generation": policy})
        self.assertEqual(templates[-1], False)  # cannot allocate thinking and preserve 15 seconds for answer


if __name__ == "__main__": unittest.main()
