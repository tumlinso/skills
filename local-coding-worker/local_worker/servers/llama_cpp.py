from __future__ import annotations

import json
import os
import shutil
import subprocess
import signal
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

from ..service import AdapterError


def _http_json(method: str, url: str, payload: dict[str, Any] | None, timeout: float) -> tuple[int, dict[str, Any]]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return int(response.status), body
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = {"error": str(error)}
        return int(error.code), body


class LlamaCppServerAdapter:
    adapter_name = "llama.cpp-server"

    def __init__(self, binary: str = "llama-server", *, process_factory=subprocess.Popen,
                 transport: Callable[[str, str, dict[str, Any] | None, float], tuple[int, dict[str, Any]]] = _http_json,
                 help_runner: Callable[..., Any] = subprocess.run,
                 sleeper: Callable[[float], None] = time.sleep) -> None:
        self.binary = binary
        self.process_factory = process_factory
        self.transport = transport
        self.help_runner = help_runner
        self.sleeper = sleeper
        self._servers: dict[str, dict[str, Any]] = {}
        self._supported_flags: set[str] | None = None

    def _flags(self, binary: str) -> set[str]:
        if self._supported_flags is None:
            result = self.help_runner([binary, "--help"], capture_output=True, text=True, timeout=10, check=False)
            text = f"{getattr(result, 'stdout', '')}\n{getattr(result, 'stderr', '')}"
            self._supported_flags = {word.rstrip(",=") for word in text.split() if word.startswith("--")}
        return self._supported_flags

    def _resolved_binary(self) -> str | None:
        if os.path.sep in self.binary:
            path = Path(self.binary)
            return str(path.resolve()) if path.is_file() and os.access(path, os.X_OK) else None
        return shutil.which(self.binary)

    def inspect(self) -> dict[str, Any]:
        resolved = self._resolved_binary()
        return {
            "adapter": self.adapter_name, "available": resolved is not None, "binary": resolved,
            "protocol": "llama.cpp-openai-http", "health_path": "/health",
            "run_path": "/v1/chat/completions",
            "capabilities": ["inspect", "start", "health", "run", "cancel", "drain", "evict", "usage"],
        }

    def start(self, context: dict[str, Any]) -> str:
        binary = self._resolved_binary()
        if binary is None:
            raise AdapterError("llama-server binary is unavailable")
        model = Path(str(context.get("model_path", ""))).resolve()
        if not model.is_file():
            raise AdapterError("llama.cpp start requires an existing local model_path")
        repo_root = context.get("repo_root")
        if repo_root:
            repo = Path(str(repo_root)).resolve()
            if model == repo or repo in model.parents:
                raise AdapterError("model weights must live outside the repository")
        host = str(context.get("host", "127.0.0.1"))
        if host not in {"127.0.0.1", "localhost", "::1"}:
            raise AdapterError("llama.cpp adapter binds loopback only")
        port = int(context.get("port", 8080))
        if not 1 <= port <= 65535:
            raise AdapterError("llama.cpp port is invalid")
        profile = dict(context.get("service_profile") or {})
        if profile and profile.get("format") != "CORE4-MODEL-SERVICE/2":
            raise AdapterError("unsupported model-service profile format")
        flags = self._flags(binary)
        argv = [binary, "--model", str(model), "--host", host, "--port", str(port)]
        options = {
            "--ctx-size": profile.get("context_size", context.get("ctx_size")),
            "--n-gpu-layers": profile.get("gpu_layers", context.get("gpu_layers")),
            "--split-mode": profile.get("split_mode"),
            "--tensor-split": profile.get("tensor_split"),
            "--main-gpu": profile.get("main_gpu"),
            "--cache-type-k": profile.get("kv_cache_type_k"),
            "--cache-type-v": profile.get("kv_cache_type_v"),
            "--numa": profile.get("numa_policy"),
            "--threads": profile.get("cpu_threads"),
        }
        for flag, value in options.items():
            if value is not None and flag in flags:
                if isinstance(value, list):
                    value = ",".join(str(item) for item in value)
                argv.extend([flag, str(value)])
        if profile.get("fit") and "--fit" in flags:
            argv.append("--fit")
        log_path = Path(str(profile.get("log_path") or context.get("log_path") or os.devnull)).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_stream = open(log_path, "a", encoding="utf-8")
        environment = os.environ.copy()
        gpu_uuids = profile.get("allocated_gpu_uuids") or context.get("allocated_gpu_uuids")
        if gpu_uuids:
            environment["CUDA_VISIBLE_DEVICES"] = ",".join(str(item) for item in gpu_uuids)
        process = self.process_factory(argv, stdout=log_stream, stderr=subprocess.STDOUT, text=True,
                                       env=environment, start_new_session=True)
        handle = str(uuid.uuid4())
        self._servers[handle] = {
            "process": process, "base_url": f"http://{host}:{port}", "accepting": True,
            "evicted": False, "canceled": set(), "log_stream": log_stream, "log_path": str(log_path),
            "profile": profile,
            "usage": {"runs": 0, "prompt_tokens": 0, "completion_tokens": 0, "duration_ms": 0.0},
        }
        timeout = float(profile.get("startup_timeout_seconds", context.get("startup_timeout_seconds", 0)))
        if timeout > 0:
            deadline = time.monotonic() + timeout
            while True:
                if process.poll() is not None:
                    self.evict(handle)
                    raise AdapterError(f"llama-server exited during startup; log: {log_path}")
                try:
                    status, _ = self.transport("GET", f"http://{host}:{port}/health", None, 2.0)
                except (OSError, urllib.error.URLError):
                    status = 0
                if status == 200:
                    break
                if time.monotonic() >= deadline:
                    self.evict(handle)
                    raise AdapterError(f"llama-server startup timed out; log: {log_path}")
                self.sleeper(min(0.1, timeout))
        return handle

    def _server(self, handle: str) -> dict[str, Any]:
        try:
            return self._servers[handle]
        except KeyError as error:
            raise AdapterError("unknown llama.cpp server handle") from error

    def health(self, handle: str) -> dict[str, Any]:
        server = self._server(handle)
        process = server["process"]
        if server["evicted"] or process.poll() is not None:
            return {"healthy": False, "state": "evicted" if server["evicted"] else "stopped"}
        status, body = self.transport("GET", server["base_url"] + "/health", None, 2.0)
        state = "draining" if not server["accepting"] else ("ready" if status == 200 else "loading")
        return {"healthy": status == 200, "state": state, "status_code": status, "details": body}

    def run(self, handle: str, request: dict[str, Any]) -> dict[str, Any]:
        server = self._server(handle)
        if server["evicted"] or not server["accepting"]:
            raise AdapterError("llama.cpp server is not accepting work")
        request_id = str(request.get("request_id") or uuid.uuid4())
        if request_id in server["canceled"]:
            return {"status": "canceled", "request_id": request_id}
        messages = request.get("messages")
        if not isinstance(messages, list) or not messages:
            raise AdapterError("llama.cpp request requires messages")
        if len(json.dumps(messages, ensure_ascii=False)) > 200_000:
            raise AdapterError("llama.cpp messages exceed the adapter payload bound")
        payload = {"messages": messages, "stream": False}
        if request.get("model"):
            payload["model"] = request["model"]
        if request.get("max_tokens") is not None:
            payload["max_tokens"] = int(request["max_tokens"])
        started = time.perf_counter()
        timeout = request.get("timeout_seconds", 600)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise AdapterError("llama.cpp timeout_seconds must be between 0 and 3600")
        status, body = self.transport("POST", server["base_url"] + "/v1/chat/completions", payload, float(timeout))
        duration = (time.perf_counter() - started) * 1000
        if status != 200:
            raise AdapterError(f"llama.cpp completion failed with HTTP {status}")
        if request_id in server["canceled"]:
            return {"status": "canceled", "request_id": request_id}
        usage = dict(body.get("usage") or {})
        server["usage"]["runs"] += 1
        server["usage"]["prompt_tokens"] += int(usage.get("prompt_tokens", 0))
        server["usage"]["completion_tokens"] += int(usage.get("completion_tokens", 0))
        server["usage"]["duration_ms"] += duration
        choices = body.get("choices") or []
        text = str((choices[0].get("message") or {}).get("content", "")) if choices else ""
        return {"status": "succeeded", "request_id": request_id, "text": text[:20_000], "usage": usage,
                "duration_ms": round(duration, 3), "raw_output_omitted_chars": max(len(text) - 20_000, 0)}

    def cancel(self, handle: str, request_id: str | None = None) -> dict[str, Any]:
        server = self._server(handle)
        if request_id:
            server["canceled"].add(request_id)
            return {"canceled": True, "request_id": request_id}
        return {"canceled": False, "reason": "request_id_required"}

    def drain(self, handle: str) -> dict[str, Any]:
        self._server(handle)["accepting"] = False
        return {"draining": True}

    def evict(self, handle: str) -> dict[str, Any]:
        server = self._server(handle)
        process = server["process"]
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except (AttributeError, ProcessLookupError, PermissionError):
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except (AttributeError, ProcessLookupError, PermissionError):
                    process.kill()
        server["log_stream"].close()
        server["accepting"] = False
        server["evicted"] = True
        return {"evicted": True}

    def quiescent(self, handle: str) -> bool:
        server = self._server(handle)
        return bool(server["evicted"] or server["process"].poll() is not None)

    def usage(self, handle: str) -> dict[str, Any]:
        usage = dict(self._server(handle)["usage"])
        usage["duration_ms"] = round(float(usage["duration_ms"]), 3)
        return usage
