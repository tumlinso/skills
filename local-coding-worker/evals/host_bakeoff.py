#!/usr/bin/env python3
"""Run the bounded CORE4 host bake-off and emit one compact structured result."""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import hashlib
import importlib.util
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import tomllib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterator


FORMAT = "CORE4-HOST-BAKEOFF/1"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


class BakeoffError(RuntimeError):
    pass


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BakeoffError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run_text(argv: list[str], *, timeout: float = 30, env: dict[str, str] | None = None,
             cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(argv, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, timeout=timeout, check=False)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def http_json(method: str, url: str, payload: dict[str, Any] | None = None,
              timeout: float = 10) -> tuple[int, dict[str, Any]]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method,
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
            return int(response.status), value if isinstance(value, dict) else {"value": value}
    except urllib.error.HTTPError as error:
        try:
            value = json.loads(error.read().decode("utf-8"))
        except Exception:
            value = {"error": str(error)}
        return int(error.code), value if isinstance(value, dict) else {"value": value}


def gpu_inventory() -> list[dict[str, Any]]:
    fields = "index,uuid,name,memory.total,memory.free,compute_cap"
    result = run_text(["nvidia-smi", f"--query-gpu={fields}", "--format=csv,noheader,nounits"])
    if result.returncode != 0:
        raise BakeoffError(f"GPU discovery failed: {result.stderr.strip()[:300]}")
    devices = []
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 6:
            continue
        devices.append({"index": int(parts[0]), "uuid": parts[1], "name": parts[2],
                        "memory_total_mib": int(parts[3]), "memory_free_mib": int(parts[4]),
                        "compute_capability": parts[5]})
    if not devices:
        raise BakeoffError("no NVIDIA GPUs discovered")
    return devices


def discover_islands(devices: list[dict[str, Any]]) -> tuple[list[list[int]], str]:
    result = run_text(["nvidia-smi", "topo", "-m"])
    if result.returncode != 0:
        raise BakeoffError(f"topology discovery failed: {result.stderr.strip()[:300]}")
    text = ANSI.sub("", result.stdout)
    count = len(devices)
    graph = {int(device["index"]): set() for device in devices}
    numa: dict[int, str] = {}
    for line in text.splitlines():
        columns = line.split()
        if not columns or not re.fullmatch(r"GPU\d+", columns[0]) or len(columns) < count + 1:
            continue
        source = int(columns[0][3:])
        for offset, link in enumerate(columns[1:1 + count]):
            target = int(devices[offset]["index"])
            if link.startswith("NV"):
                graph[source].add(target)
                graph[target].add(source)
        if len(columns) > count + 2:
            numa[source] = columns[count + 2]
    islands: list[list[int]] = []
    pending = set(graph)
    while pending:
        root = min(pending)
        stack = [root]
        component = set()
        while stack:
            item = stack.pop()
            if item in component:
                continue
            component.add(item)
            stack.extend(graph[item] - component)
        pending -= component
        islands.append(sorted(component))
    if all(len(item) == 1 for item in islands) and numa:
        grouped: dict[str, list[int]] = {}
        for index in sorted(graph):
            grouped.setdefault(numa.get(index, str(index)), []).append(index)
        islands = list(grouped.values())
    return sorted(islands, key=lambda item: (len(item), item), reverse=True), text


def gpu_memory(indices: list[int]) -> dict[str, Any]:
    result = run_text(["nvidia-smi", "--query-gpu=index,memory.used,memory.free,utilization.gpu",
                       "--format=csv,noheader,nounits"])
    rows = {}
    for line in result.stdout.splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 4 and int(parts[0]) in indices:
            rows[parts[0]] = {"memory_used_mib": int(parts[1]), "memory_free_mib": int(parts[2]),
                              "utilization_percent": int(parts[3])}
    return rows


class ResourceLease:
    def __init__(self, repo: Path, devices: list[dict[str, Any]], indices: list[int]) -> None:
        sys.path.insert(0, str(repo / "todo-orchestrator"))
        from todo_orchestrator.runtime import RuntimeFacade
        self.facade = RuntimeFacade(repo).host
        self.repo = repo
        self.devices = devices
        self.indices = indices
        self.reservation: dict[str, object] | None = None

    def __enter__(self) -> "ResourceLease":
        facts = [{"id": f"accelerator:{item['uuid']}", "kind": "accelerator",
                  "tags": {"architecture": "sm_70", "index": str(item["index"])}}
                 for item in self.devices]
        self.facade.upsert(facts)
        selected = [item for item in self.devices if int(item["index"]) in self.indices]
        request = {"schema_version": 1, "kind": "accelerator",
                   "ids": [f"accelerator:{item['uuid']}" for item in selected],
                   "ram_bytes": 8 * 1024 * 1024 * 1024}
        self.reservation = self.facade.begin_foreground(project_root=self.repo, resource_request=request)
        deadline = time.monotonic() + 120
        while not self.facade.activate_foreground(self.reservation):
            if time.monotonic() >= deadline:
                self.facade.release(str(self.reservation["owner_id"]))
                raise BakeoffError("timed out waiting for host-global GPU resources")
            self.facade.heartbeat(str(self.reservation["owner_id"]))
            time.sleep(1)
        return self

    def heartbeat(self) -> None:
        if self.reservation:
            self.facade.heartbeat(str(self.reservation["owner_id"]))

    def __exit__(self, *_args) -> None:
        if self.reservation:
            self.facade.release(str(self.reservation["owner_id"]))


class Server:
    def __init__(self, config: dict[str, Any], model: Path, candidate_id: str, context: int,
                 indices: list[int], port: int, raw_dir: Path) -> None:
        self.config = config
        self.model = model
        self.candidate_id = candidate_id
        self.context = context
        self.indices = indices
        self.port = port
        self.raw_dir = raw_dir
        self.process: subprocess.Popen[str] | None = None
        self.log_handle = None
        self.load_seconds = 0.0

    @property
    def base_url(self) -> str:
        return f"http://{self.config['host']}:{self.port}"

    def __enter__(self) -> "Server":
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.raw_dir / f"server-{self.port}.log"
        self.log_handle = log_path.open("w", encoding="utf-8")
        argv = [self.config["binary"], "--model", str(self.model), "--host", self.config["host"],
                "--port", str(self.port), "--ctx-size", str(self.context), "--n-gpu-layers",
                str(self.config["gpu_layers"]), "--split-mode", self.config["split_mode"],
                "--parallel", "1", "--no-webui", "--metrics", "--flash-attn", "auto"]
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = ",".join(str(item) for item in self.indices)
        started = time.perf_counter()
        self.process = subprocess.Popen(argv, env=env, text=True, stdout=self.log_handle,
                                        stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + float(self.config["startup_timeout_seconds"])
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise BakeoffError(f"llama.cpp exited during load for {self.candidate_id}; see {log_path}")
                try:
                    status, body = http_json("GET", self.base_url + "/health", timeout=2)
                    if status == 200 and body.get("status") in {"ok", "ready", None}:
                        self.load_seconds = time.perf_counter() - started
                        return self
                except (OSError, urllib.error.URLError, TimeoutError):
                    pass
                time.sleep(2)
            raise BakeoffError(f"llama.cpp startup timed out for {self.candidate_id}; see {log_path}")
        except BaseException:
            self._stop()
            raise

    def completion(self, prompt: str, *, max_tokens: int = 96) -> dict[str, Any]:
        started = time.perf_counter()
        status, body = http_json("POST", self.base_url + "/v1/chat/completions", {
            "model": self.candidate_id, "messages": [{"role": "user", "content": prompt}],
            "stream": False, "max_tokens": max_tokens, "temperature": 0,
        }, timeout=float(self.config["request_timeout_seconds"]))
        duration = time.perf_counter() - started
        if status != 200:
            raise BakeoffError(f"completion failed with HTTP {status}: {str(body)[:300]}")
        choices = body.get("choices") or []
        text = str((choices[0].get("message") or {}).get("content", "")) if choices else ""
        return {"text": text, "usage": dict(body.get("usage") or {}), "wall_seconds": round(duration, 3)}

    def _stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.log_handle:
            self.log_handle.close()
            self.log_handle = None

    def __exit__(self, *_args) -> None:
        self._stop()


def parse_qwen(stdout: str) -> tuple[str, dict[str, Any], int]:
    value = json.loads(stdout)
    records = value if isinstance(value, list) else [value]
    result = next((item for item in reversed(records)
                   if isinstance(item, dict) and item.get("type") == "result"), None)
    if result is None:
        raise BakeoffError("qwen did not emit a result record")
    tool_calls = sum(1 for item in records if isinstance(item, dict) and
                     ("tool" in str(item.get("type", "")).lower() or item.get("tool_name")))
    return str(result.get("result", "")), dict(result.get("usage") or {}), tool_calls


def run_qwen(binary: str, repo: Path, server: Server, task: dict[str, Any], harness: dict[str, Any],
             raw_path: Path) -> dict[str, Any]:
    argv = [binary, "--prompt", task["prompt"], "--output-format", "json", "--safe-mode",
            "--approval-mode", "plan", "--exclude-tools", "agent,shell,write,edit",
            "--max-session-turns", str(harness["qwen_max_session_turns"]), "--max-wall-time",
            str(harness["qwen_max_wall_time_seconds"]), "--max-tool-calls",
            str(harness["qwen_max_tool_calls"]), "--model", server.candidate_id]
    env = dict(os.environ)
    env.update({"OPENAI_API_KEY": "core4-local-no-auth", "OPENAI_BASE_URL": server.base_url + "/v1",
                "OPENAI_MODEL": server.candidate_id})
    started = time.perf_counter()
    result = run_text(argv, timeout=float(harness["qwen_max_wall_time_seconds"]) + 30, env=env, cwd=repo)
    elapsed = time.perf_counter() - started
    raw_path.write_text(json.dumps({"argv": argv[:1] + ["<bounded-options>"], "returncode": result.returncode,
                                    "stdout": result.stdout, "stderr": result.stderr}, indent=2), encoding="utf-8")
    if result.returncode != 0:
        raise BakeoffError(f"qwen exited {result.returncode}: {result.stderr.strip()[:300]}")
    text, usage, tool_calls = parse_qwen(result.stdout)
    return graded(task, text, usage, tool_calls, elapsed, "qwen-code", raw_path)


def run_codex(binary: str, repo: Path, server: Server, task: dict[str, Any], profile: str,
              raw_path: Path) -> dict[str, Any]:
    argv = [binary, "exec", "--profile", profile, "--model", server.candidate_id, "--json",
            "--ephemeral", "--sandbox", "read-only", "--ask-for-approval", "never",
            "--cd", str(repo), task["prompt"]]
    started = time.perf_counter()
    result = run_text(argv, timeout=330, cwd=repo)
    elapsed = time.perf_counter() - started
    raw_path.write_text(json.dumps({"argv": argv[:-1] + ["<bounded-prompt>"], "returncode": result.returncode,
                                    "stdout": result.stdout, "stderr": result.stderr}, indent=2), encoding="utf-8")
    if result.returncode != 0:
        raise BakeoffError(f"codex exited {result.returncode}: {result.stderr.strip()[:300]}")
    records = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    messages = [str(item.get("item", {}).get("text", "")) for item in records
                if item.get("type") == "item.completed" and item.get("item", {}).get("type") == "agent_message"]
    usage = next((dict(item.get("usage") or {}) for item in reversed(records)
                  if item.get("type") == "turn.completed"), {})
    tool_calls = sum(1 for item in records if item.get("type") == "item.completed" and
                     item.get("item", {}).get("type") in {"command_execution", "mcp_tool_call"})
    if not messages:
        raise BakeoffError("codex did not emit an agent message")
    return graded(task, messages[-1], usage, tool_calls, elapsed, "codex-cli", raw_path)


def graded(task: dict[str, Any], text: str, usage: dict[str, Any], tool_calls: int,
           elapsed: float, harness: str, raw_path: Path) -> dict[str, Any]:
    folded = text.casefold()
    accepted = all(str(item).casefold() in folded for item in task["expected_all"])
    return {"task_id": task["id"], "harness": harness, "accepted": accepted,
            "outcome": "NEEDS_CODEX" if "needs_codex" in folded else "answer",
            "prompt_chars": len(task["prompt"]), "result_chars": len(text),
            "codex_visible_input_bytes": len(task["prompt"].encode()),
            "codex_visible_output_bytes": len(text[:20000].encode()),
            "local_prompt_tokens": int(usage.get("prompt_tokens", usage.get("input_tokens", 0)) or 0),
            "local_completion_tokens": int(usage.get("completion_tokens", usage.get("output_tokens", 0)) or 0),
            "local_tool_calls": tool_calls, "frontier_rework_required": 0 if accepted else 1,
            "wall_seconds": round(elapsed, 3), "raw_evidence": str(raw_path)}


def load_tasks(path: Path) -> dict[str, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != "CORE4-HOST-TASKS/1":
        raise BakeoffError("task corpus format is invalid")
    tasks = {item["id"]: item for item in document.get("tasks", [])}
    if not tasks:
        raise BakeoffError("task corpus is empty")
    return tasks


def model_file(staged: dict[str, Any], candidate: dict[str, Any]) -> Path:
    path = Path(staged["staged_dir"]) / candidate["artifact"]
    if not path.is_file():
        raise BakeoffError(f"staged artifact is missing: {path}")
    return path


def candidate_indices(candidate: dict[str, Any], islands: list[list[int]], devices: list[dict[str, Any]]) -> list[int]:
    if candidate["profile"] == "all-gpu-single-wide":
        return sorted(int(item["index"]) for item in devices)
    eligible = [item for item in islands if len(item) >= 2]
    return sorted((eligible[0] if eligible else islands[0]))


def evaluate_candidate(repo: Path, config: dict[str, Any], candidate: dict[str, Any],
                       tasks: dict[str, dict[str, Any]], task_ids: list[str], islands: list[list[int]],
                       devices: list[dict[str, Any]], staging: Any, raw_root: Path,
                       *, context: int, harness_name: str = "qwen") -> dict[str, Any]:
    candidate_id = candidate["id"]
    indices = candidate_indices(candidate, islands, devices)
    record: dict[str, Any] = {"candidate_id": candidate_id, "family": candidate["family"],
                              "quantization": candidate["quantization"], "context_size": context,
                              "gpu_indices": indices, "gpu_profile": candidate["profile"],
                              "worker_layout": "one-worker", "harness": harness_name, "tasks": []}
    started = time.perf_counter()
    raw_dir = raw_root / candidate_id / f"{context}-{harness_name}"
    try:
        stage_started = time.perf_counter()
        with staging.staged_candidate(staging.load_policy(repo / "local-coding-worker/config/production-profile.toml"), candidate_id) as staged:
            record["staging_seconds"] = round(time.perf_counter() - stage_started, 3)
            record["canonical_verification"] = {"source": staged["source"], "payload_bytes": staged["payload_bytes"]}
            with ResourceLease(repo, devices, indices) as lease:
                with Server(config["server"], model_file(staged, candidate), candidate_id, context,
                            indices, int(config["server"]["base_port"]), raw_dir) as server:
                    record["model_load_seconds"] = round(server.load_seconds, 3)
                    record["gpu_after_load"] = gpu_memory(indices)
                    probe = server.completion("Reply with exactly CORE4_OK.", max_tokens=16)
                    record["server_probe"] = {"ok": "CORE4_OK" in probe["text"],
                                                "wall_seconds": probe["wall_seconds"], "usage": probe["usage"]}
                    if not record["server_probe"]["ok"]:
                        raise BakeoffError("server viability probe did not return CORE4_OK")
                    for task_id in task_ids:
                        lease.heartbeat()
                        task = tasks[task_id]
                        raw_path = raw_dir / f"{task_id}.json"
                        if harness_name == "qwen":
                            result = run_qwen(config["harnesses"]["qwen"], repo, server, task,
                                              config["harnesses"], raw_path)
                        else:
                            result = run_codex(config["harnesses"]["codex"], repo, server, task,
                                               config["harnesses"]["codex_profile"], raw_path)
                        record["tasks"].append(result)
                    record["gpu_after_tasks"] = gpu_memory(indices)
        record["status"] = "completed"
    except Exception as error:
        record["status"] = "eliminated"
        record["reason"] = str(error)[:500]
    record["wall_seconds"] = round(time.perf_counter() - started, 3)
    accepted = sum(bool(item.get("accepted")) for item in record["tasks"])
    record["accepted_tasks"] = accepted
    record["acceptance_rate"] = accepted / len(record["tasks"]) if record["tasks"] else 0.0
    return record


def economics(record: dict[str, Any]) -> tuple[Any, ...]:
    tasks = record.get("tasks", [])
    accepted = sum(bool(item.get("accepted")) for item in tasks)
    visible = sum(int(item.get("codex_visible_input_bytes", 0)) + int(item.get("codex_visible_output_bytes", 0)) for item in tasks)
    rework = sum(int(item.get("frontier_rework_required", 0)) for item in tasks)
    return (-accepted, rework, visible, float(record.get("wall_seconds", 1e18)))


def topology_refinement(repo: Path, config: dict[str, Any], candidate: dict[str, Any],
                        tasks: dict[str, dict[str, Any]], islands: list[list[int]],
                        devices: list[dict[str, Any]], staging: Any, raw_root: Path,
                        context: int, baseline: dict[str, Any]) -> dict[str, Any]:
    """Measure conservative, two-worker, and single-wide arms in one staged lifetime."""
    arms: list[dict[str, Any]] = [{
        "layout": "one-worker-one-island", "source": "phase-D",
        "accepted_tasks": baseline.get("accepted_tasks", 0),
        "wall_seconds": baseline.get("wall_seconds"),
        "tasks_per_hour": round(3600 * baseline.get("accepted_tasks", 0) /
                                max(float(baseline.get("wall_seconds", 1)), 0.001), 4),
        "gpu_indices": baseline.get("gpu_indices", []),
    }]
    island_pairs = [item for item in islands if len(item) >= 2]
    all_indices = sorted(int(item["index"]) for item in devices)
    policy = staging.load_policy(repo / "local-coding-worker/config/production-profile.toml")
    raw_dir = raw_root / candidate["id"] / f"{context}-topology"
    stage_started = time.perf_counter()
    with staging.staged_candidate(policy, candidate["id"]) as staged:
        stage_seconds = time.perf_counter() - stage_started
        model = model_file(staged, candidate)
        if len(island_pairs) >= 2:
            selected = sorted(island_pairs[:2])
            started = time.perf_counter()
            arm: dict[str, Any] = {"layout": "two-workers-two-islands", "gpu_islands": selected,
                                   "tasks": [], "staging_seconds": round(stage_seconds, 3)}
            try:
                with ResourceLease(repo, devices, sorted(set(selected[0] + selected[1]))):
                    with Server(config["server"], model, candidate["id"], context, selected[0],
                                int(config["server"]["base_port"]), raw_dir / "worker-0") as first, \
                         Server(config["server"], model, candidate["id"], context, selected[1],
                                int(config["server"]["base_port"]) + 1, raw_dir / "worker-1") as second:
                        selected_tasks = [tasks[item] for item in config["experiment"]["phase_b_task_ids"][:2]]
                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                            futures = [
                                pool.submit(run_qwen, config["harnesses"]["qwen"], repo, server, task,
                                            config["harnesses"], raw_dir / f"worker-{offset}" / f"{task['id']}.json")
                                for offset, (server, task) in enumerate(zip((first, second), selected_tasks))
                            ]
                            arm["tasks"] = [future.result() for future in futures]
                        arm["model_load_seconds"] = round(max(first.load_seconds, second.load_seconds), 3)
                arm["status"] = "completed"
            except Exception as error:
                arm.update({"status": "failed", "reason": str(error)[:500]})
            arm["wall_seconds"] = round(time.perf_counter() - started, 3)
            arm["accepted_tasks"] = sum(bool(item.get("accepted")) for item in arm["tasks"])
            arm["tasks_per_hour"] = round(3600 * arm["accepted_tasks"] / max(arm["wall_seconds"], 0.001), 4)
            arms.append(arm)
        started = time.perf_counter()
        arm = {"layout": "one-worker-all-gpu-single-wide", "gpu_indices": all_indices,
               "tasks": [], "staging_seconds": round(stage_seconds, 3)}
        try:
            with ResourceLease(repo, devices, all_indices):
                with Server(config["server"], model, candidate["id"], context, all_indices,
                            int(config["server"]["base_port"]), raw_dir / "single-wide") as server:
                    for task_id in config["experiment"]["phase_b_task_ids"][:2]:
                        arm["tasks"].append(run_qwen(config["harnesses"]["qwen"], repo, server,
                                                    tasks[task_id], config["harnesses"],
                                                    raw_dir / "single-wide" / f"{task_id}.json"))
                    arm["model_load_seconds"] = round(server.load_seconds, 3)
            arm["status"] = "completed"
        except Exception as error:
            arm.update({"status": "failed", "reason": str(error)[:500]})
        arm["wall_seconds"] = round(time.perf_counter() - started, 3)
        arm["accepted_tasks"] = sum(bool(item.get("accepted")) for item in arm["tasks"])
        arm["tasks_per_hour"] = round(3600 * arm["accepted_tasks"] / max(arm["wall_seconds"], 0.001), 4)
        arms.append(arm)
    eligible = [item for item in arms if item.get("status", "completed") == "completed" and
                int(item.get("accepted_tasks", 0)) > 0]
    eligible.sort(key=lambda item: (-int(item["accepted_tasks"]), -float(item["tasks_per_hour"]),
                                    0 if item["layout"] == "one-worker-one-island" else 1))
    winner = eligible[0] if eligible else arms[0]
    conservative = next(item for item in arms if item["layout"] == "one-worker-one-island")
    promote = winner["layout"] != conservative["layout"] and float(winner.get("tasks_per_hour", 0)) > \
        float(conservative.get("tasks_per_hour", 0)) * 1.15
    return {"arms": arms, "recommended": winner["layout"] if promote else conservative["layout"],
            "promotion_threshold": "more than 15% accepted-task throughput", "promoted": promote}


def validate(repo: Path, config: dict[str, Any], tasks: dict[str, dict[str, Any]], staging: Any) -> dict[str, Any]:
    devices = gpu_inventory()
    islands, topology = discover_islands(devices)
    missing = []
    policy = staging.load_policy(repo / "local-coding-worker/config/production-profile.toml")
    for candidate in config["candidates"]:
        try:
            directory = policy.canonical_root / candidate["id"]
            manifest = staging._load_asset_manifest(directory, candidate["id"])
            if not (directory / candidate["artifact"]).is_file() or not manifest:
                missing.append(candidate["id"])
        except Exception:
            missing.append(candidate["id"])
    executables = {name: shutil.which(path) if os.path.sep not in path else path
                   for name, path in {"server": config["server"]["binary"],
                                      "qwen": config["harnesses"]["qwen"],
                                      "codex": config["harnesses"]["codex"]}.items()}
    if missing or any(not value or not Path(value).is_file() for value in executables.values()):
        raise BakeoffError(f"validation failed: missing_candidates={missing} executables={executables}")
    node = run_text(["node", "--version"])
    match = re.fullmatch(r"v(\d+)\.\d+\.\d+\s*", node.stdout)
    node_major = int(match.group(1)) if node.returncode == 0 and match else 0
    required_node = int(config["harnesses"]["qwen_minimum_node_major"])
    if node_major < required_node:
        raise BakeoffError(
            f"Qwen Code runtime requires Node >={required_node}; active node is "
            f"{node.stdout.strip() or 'unavailable'} at {shutil.which('node')}"
        )
    required_tasks = set(config["experiment"]["phase_a_task_ids"] + config["experiment"]["phase_b_task_ids"])
    if not required_tasks <= set(tasks):
        raise BakeoffError(f"task corpus missing ids: {sorted(required_tasks - set(tasks))}")
    return {"gpu_count": len(devices), "islands": islands, "topology_sha256": hashlib.sha256(topology.encode()).hexdigest(),
            "candidate_count": len(config["candidates"]), "task_count": len(tasks), "executables": executables}


def main() -> int:
    def interrupt(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, interrupt)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    repo = Path(args.repo).resolve()
    config_path = repo / "local-coding-worker/config/production-profile.toml"
    config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    if config.get("format") != "CORE4-PRODUCTION-PROFILE/1":
        raise BakeoffError("production profile format is invalid")
    tasks = load_tasks(repo / "local-coding-worker/evals/tasks/core4-host-tasks.json")
    staging = load_module("core4_model_staging", repo / "local-coding-worker/evals/model_staging.py")
    validation = validate(repo, config, tasks, staging)
    if args.validate_only:
        print(json.dumps({"format": FORMAT, "validation": validation, "valid": True}, separators=(",", ":")))
        return 0
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_root = output.parent / "raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    devices = gpu_inventory()
    islands, topology = discover_islands(devices)
    source_head = run_text(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    topology_sha256 = hashlib.sha256(topology.encode()).hexdigest()
    result: dict[str, Any] | None = None
    if output.is_file():
        try:
            previous = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            previous = {}
        if (previous.get("format") == FORMAT and previous.get("status") == "running" and
                previous.get("source_head") == source_head and previous.get("validation") == validation and
                previous.get("topology", {}).get("sha256") == topology_sha256):
            result = previous
    if result is None:
        result = {"format": FORMAT, "schema_version": 1, "started_at": time.time(),
                  "source_head": source_head, "validation": validation,
                  "topology": {"islands": islands, "sha256": topology_sha256},
                  "phases": {}, "status": "running"}
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    phase_a = list(result["phases"].get("A", []))
    phase_a_ids = {item["candidate_id"] for item in phase_a}
    for candidate in config["candidates"]:
        if candidate["id"] in phase_a_ids:
            continue
        record = evaluate_candidate(repo, config, candidate, tasks, config["experiment"]["phase_a_task_ids"],
                                    islands, devices, staging, raw_root, context=config["experiment"]["initial_context"])
        phase_a.append(record)
        result["phases"]["A"] = phase_a
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    survivors = [item for item in phase_a if item["status"] == "completed" and
                 item["acceptance_rate"] >= float(config["experiment"]["minimum_phase_a_acceptance"]) and
                 item["wall_seconds"] <= float(config["experiment"]["maximum_phase_a_seconds_per_task"]) +
                 float(item.get("staging_seconds", 0)) + float(item.get("model_load_seconds", 0))]
    if not survivors:
        raise BakeoffError("phase A eliminated every candidate")
    survivor_ids = {item["candidate_id"] for item in survivors}
    phase_b = list(result["phases"].get("B", []))
    phase_b_ids = {item["candidate_id"] for item in phase_b}
    for candidate in config["candidates"]:
        if candidate["id"] not in survivor_ids or candidate["id"] in phase_b_ids:
            continue
        phase_b.append(evaluate_candidate(repo, config, candidate, tasks, config["experiment"]["phase_b_task_ids"],
                                          islands, devices, staging, raw_root,
                                          context=config["experiment"]["initial_context"]))
        result["phases"]["B"] = phase_b
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    serious = [item for item in phase_b if item["status"] == "completed" and
               item["acceptance_rate"] >= float(config["experiment"]["minimum_phase_b_acceptance"])]
    if not serious:
        result["selection"] = None
        result["summary"] = {"evaluated_candidates": len(phase_a),
                             "phase_a_survivors": len(survivors), "phase_b_survivors": 0,
                             "eliminated": [{"candidate_id": item["candidate_id"],
                                             "reason": item.get("reason", "phase B acceptance threshold")}
                                            for item in phase_b],
                             "raw_evidence_root": str(raw_root)}
        result["status"] = "completed"
        result["disposition"] = "evaluated_not_promoted"
        result["finished_at"] = time.time()
        result["result_sha256"] = "pending"
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        result["result_sha256"] = sha256(output)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"format": FORMAT, "status": result["status"],
                          "disposition": result["disposition"], "selection": None,
                          "summary": result["summary"], "output": str(output)}, separators=(",", ":")))
        return 0
    serious.sort(key=economics)
    best = serious[0]
    best_candidate = next(item for item in config["candidates"] if item["id"] == best["candidate_id"])
    family_records = [item for item in serious if item["family"] == best["family"]]
    family_records.sort(key=economics)
    selected_quant = family_records[0]
    selected_candidate = next(item for item in config["candidates"] if item["id"] == selected_quant["candidate_id"])
    phase_d = []
    for context in config["experiment"]["refinement_contexts"]:
        phase_d.append(evaluate_candidate(repo, config, selected_candidate, tasks,
                                          config["experiment"]["phase_b_task_ids"], islands, devices,
                                          staging, raw_root, context=context))
        result["phases"]["D"] = phase_d
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    context_survivors = [item for item in phase_d if item["status"] == "completed"]
    context_survivors.sort(key=economics)
    selected_context = context_survivors[0] if context_survivors else selected_quant
    phase_e = [evaluate_candidate(repo, config, selected_candidate, tasks,
                                  config["experiment"]["phase_b_task_ids"], islands, devices,
                                  staging, raw_root, context=selected_context["context_size"], harness_name="codex")]
    result["phases"]["E"] = phase_e
    qwen_record = selected_context
    codex_record = phase_e[0]
    harness_recommendation = "codex-cli" if codex_record["status"] == "completed" and economics(codex_record) < economics(qwen_record) else "qwen-code"
    phase_f = topology_refinement(repo, config, selected_candidate, tasks, islands, devices,
                                  staging, raw_root, selected_context["context_size"], selected_context)
    result["phases"]["F"] = phase_f
    result["selection"] = {"candidate_id": selected_candidate["id"], "family": selected_candidate["family"],
                           "quantization": selected_candidate["quantization"],
                           "context_size": selected_context["context_size"],
                           "harness": harness_recommendation, "worker_layout": phase_f["recommended"],
                           "decisive": True, "objective": "minimum frontier-visible work per accepted task"}
    result["summary"] = {"evaluated_candidates": len(phase_a), "phase_a_survivors": len(survivors),
                         "phase_b_survivors": len(serious),
                         "eliminated": [{"candidate_id": item["candidate_id"], "reason": item.get("reason", "acceptance or time threshold")}
                                        for item in phase_a if item not in survivors],
                         "raw_evidence_root": str(raw_root)}
    result["status"] = "completed"
    result["finished_at"] = time.time()
    result["result_sha256"] = "pending"
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    result["result_sha256"] = sha256(output)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"format": FORMAT, "status": result["status"], "selection": result["selection"],
                      "summary": result["summary"], "output": str(output)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as error:
        print(json.dumps({"format": FORMAT, "status": "failed", "error": str(error)[:1000]}, separators=(",", ":")), file=sys.stderr)
        raise SystemExit(2)
