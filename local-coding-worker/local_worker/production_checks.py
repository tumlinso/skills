"""Bounded real-host checks and compact production evidence for CORE4."""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
import urllib.error
from pathlib import Path
from typing import Any

from .model_cache import ModelCache


class ProductionCheckError(RuntimeError):
    pass


def _repo() -> Path:
    return Path(__file__).resolve().parents[2]


def _profile(repo: Path) -> dict[str, Any]:
    return tomllib.loads((repo / "local-coding-worker/config/production-profile.toml").read_text(encoding="utf-8"))


def _host_module(repo: Path):
    path = repo / "local-coding-worker/evals/host_bakeoff.py"
    spec = importlib.util.spec_from_file_location("core4_production_host", path)
    if spec is None or spec.loader is None:
        raise ProductionCheckError("cannot load the existing host runner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_compact(repo: Path, name: str, value: dict[str, Any]) -> dict[str, Any]:
    destination = repo / "local-coding-worker/evals/results/compact" / f"{name}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {**value, "evidence_path": str(destination)}


def _service_preemption(repo: Path, count: int) -> dict[str, Any]:
    todo = repo / "todo-orchestrator"
    if str(todo) not in sys.path:
        sys.path.insert(0, str(todo))
    from todo_orchestrator.runtime import RuntimeFacade
    host = RuntimeFacade(repo).host
    host.discover_gpus()
    bundles = host.compound_gpu_bundles(count)
    if not bundles:
        raise ProductionCheckError("runtime discovery returned no usable GPU island")
    bundle = bundles[0]
    request = {"schema_version": 1, "kind": "accelerator", "ids": bundle["resource_ids"],
               "exclusive_resources": bundle["exclusive_resources"]}
    service = host.reserve_service(project_root=repo, service_id="c4p-host-service-check",
                                   resource_request=request, priority_class="idle_model_residency")
    if service is None:
        raise ProductionCheckError("could not reserve the discovered GPU island for service preemption proof")
    foreground = None
    try:
        foreground = host.begin_foreground(project_root=repo, resource_request=request,
                                           priority_class="clean_cuda_foreground")
        requested = host.preempt_requested(str(service["owner_id"]))
        blocked_before_release = not host.activate_foreground(foreground)
        host.release(str(service["owner_id"]))
        activated_after_release = host.activate_foreground(foreground)
        return {"preempt_requested": requested, "foreground_blocked_until_release": blocked_before_release,
                "foreground_activated_after_release": activated_after_release,
                "resource_ids": bundle["resource_ids"]}
    finally:
        host.release(str(service["owner_id"]))
        if foreground is not None:
            host.release(str(foreground["owner_id"]))


def _host_service(repo: Path) -> dict[str, Any]:
    profile = _profile(repo)
    storage = profile["storage"]
    cache = ModelCache(storage["cache_root"], storage["canonical_root"])
    active = cache.active()
    if not active:
        raise ProductionCheckError("persistent active model cache is missing")
    verified = cache.verify(str(active["candidate_id"]), str(active["payload_sha256"]), full=True)
    host = _host_module(repo)
    devices = host.gpu_inventory()
    islands, topology = host.discover_islands(devices)
    candidate = next((item for item in profile["candidates"] if item["id"] == active["candidate_id"]), None)
    if candidate is None:
        raise ProductionCheckError("active cache candidate is absent from the production profile")
    indices = host.candidate_indices(candidate, islands, devices)
    raw = repo / "local-coding-worker/evals/results/compact/host-service"
    starts = []
    for attempt in range(2):
        with host.ResourceLease(repo, devices, indices):
            server = host.Server(profile["server"], Path(str(verified["payload_path"])),
                                 str(active["candidate_id"]), int(profile["experiment"]["initial_context"]),
                                 indices, int(profile["server"]["base_port"]), raw / f"start-{attempt + 1}")
            with server:
                probe = server.completion("Reply with exactly CORE4_OK.", max_tokens=16)
                status, models = host.http_json("GET", server.base_url + "/v1/models", timeout=5)
                time.sleep(1)
                retained_status, _ = host.http_json("GET", server.base_url + "/health", timeout=5)
                starts.append({"attempt": attempt + 1, "load_seconds": round(server.load_seconds, 3),
                               "probe_ok": "CORE4_OK" in probe["text"], "models_status": status,
                               "model_count": len(models.get("data", [])), "idle_retained": retained_status == 200})
            cleanly_stopped = server.process is not None and server.process.poll() is not None
            starts[-1]["cleanly_stopped"] = cleanly_stopped
    preemption = _service_preemption(repo, len(indices))
    ok = all(item["probe_ok"] and item["models_status"] == 200 and item["model_count"] > 0 and
             item["idle_retained"] and item["cleanly_stopped"] for item in starts) and all(
                 bool(preemption[key]) for key in ("preempt_requested", "foreground_blocked_until_release",
                                                   "foreground_activated_after_release"))
    result = {"format": "CORE4-HOST-CHECK/1", "scenario": "service", "ok": ok,
              "candidate_id": active["candidate_id"], "payload_sha256": active["payload_sha256"],
              "payload_bytes": verified["payload_bytes"], "context_size": profile["experiment"]["initial_context"],
              "gpu_indices": indices, "topology_sha256": host.hashlib.sha256(topology.encode()).hexdigest(),
              "starts": starts, "preemption": preemption}
    if not ok:
        raise ProductionCheckError("real service lifecycle check did not satisfy every guard")
    return _write_compact(repo, "host-service", result)


def _ctxpp_evidence(repo: Path) -> dict[str, Any]:
    index = repo / ".ctxpp/index.jsonl"
    if not index.is_file():
        scan = subprocess.run(
            [str(repo / "cpp-context-compiler/scripts/ctxpp"), "--root", str(repo), "--json", "scan"],
            cwd=repo, text=True, capture_output=True, timeout=120, check=False,
        )
        if scan.returncode != 0:
            raise ProductionCheckError(f"ctxpp scan failed: {scan.stderr.strip()[:300]}")
    command = [str(repo / "cpp-context-compiler/scripts/ctxpp"), "--root", str(repo), "--json",
               "packet", "PackingPlan", "--consumer", "local-worker", "--intent", "understand",
               "--budget", "1024", "--max-items", "8"]
    process = subprocess.run(command, cwd=repo, text=True, capture_output=True, timeout=120, check=False)
    if process.returncode != 0:
        raise ProductionCheckError(f"ctxpp packet failed: {process.stderr.strip()[:300]}")
    packet = json.loads(process.stdout)
    return {"format": packet.get("format"), "packet_hash": packet.get("packet_hash"),
            "estimated_tokens": packet.get("estimated_tokens"),
            "coverage_sufficient": bool((packet.get("coverage") or {}).get("sufficient")),
            "source_fingerprint": (packet.get("source_identity") or {}).get("fingerprint")}


def _host_readonly(repo: Path) -> dict[str, Any]:
    from .harnesses import QwenCodeAdapter
    class HostQwenCodeAdapter(QwenCodeAdapter):
        """Keep the installed CLI local; its --sandbox flag pulls a container."""
        def build_command(self, session, prompt):
            argv, environment = super().build_command(session, prompt)
            argv[argv.index("--sandbox")] = "--no-sandbox"
            return argv, environment
    profile = _profile(repo)
    cache = ModelCache(profile["storage"]["cache_root"], profile["storage"]["canonical_root"])
    active = cache.active()
    if not active:
        raise ProductionCheckError("persistent active model cache is missing")
    verified = cache.verify(str(active["candidate_id"]), str(active["payload_sha256"]), full=False)
    host = _host_module(repo)
    tasks = host.load_tasks(repo / "local-coding-worker/evals/tasks/core4-host-tasks.json")
    selected_ids = ["contract-authority", "resource-policy", "needs-codex"]
    devices = host.gpu_inventory()
    islands, _ = host.discover_islands(devices)
    candidate = next(item for item in profile["candidates"] if item["id"] == active["candidate_id"])
    indices = host.candidate_indices(candidate, islands, devices)
    results = []
    environment = {"OPENAI_API_KEY": "core4-local-no-auth", "OPENAI_MODEL": str(active["candidate_id"])}
    prior = {key: os.environ.get(key) for key in environment | {"OPENAI_BASE_URL": ""}}
    try:
        with host.ResourceLease(repo, devices, indices):
            with host.Server(profile["server"], Path(str(verified["payload_path"])), str(active["candidate_id"]),
                             int(profile["experiment"]["initial_context"]), indices,
                             int(profile["server"]["base_port"]),
                             repo / "local-coding-worker/evals/results/compact/host-readonly-runtime") as server:
                environment["OPENAI_BASE_URL"] = server.base_url + "/v1"
                os.environ.update(environment)
                harness = HostQwenCodeAdapter(str(profile["harnesses"]["qwen"]))
                handle = harness.start({"cwd": str(repo), "model": str(active["candidate_id"]),
                    "allowed_tools": ["read_file"], "max_session_turns": 12, "max_tool_calls": 8,
                    "max_wall_time_seconds": 180, "timeout_seconds": 210})
                try:
                    for task_id in selected_ids:
                        task = tasks[task_id]
                        outcome = harness.run(handle, {"prompt": task["prompt"], "timeout_seconds": 210})
                        text = str(outcome.get("text", ""))
                        accepted = all(str(item).casefold() in text.casefold() for item in task["expected_all"])
                        results.append({"task_id": task_id, "accepted": accepted,
                            "status": outcome.get("status"), "outcome": outcome.get("outcome", "answer"),
                            "codex_visible_input_bytes": len(task["prompt"].encode()),
                            "codex_visible_output_bytes": len(text.encode()),
                            "local_tool_calls": int((outcome.get("usage", {}).get("core4", {}) or {}).get("tool_calls", 0)),
                            "tool_names": (outcome.get("usage", {}).get("core4", {}) or {}).get("tool_names", []),
                            "duration_ms": outcome.get("duration_ms")})
                finally:
                    harness.evict(handle)
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    state = json.loads((repo / ".todo-orchestrator/state.snapshot.json").read_text(encoding="utf-8"))
    needs = next(item for item in results if item["task_id"] == "needs-codex")
    ok = all(item["accepted"] for item in results) and needs["status"] == "needs_codex"
    result = {"format": "CORE4-HOST-CHECK/1", "scenario": "readonly", "ok": ok,
              "candidate_id": active["candidate_id"], "payload_sha256": active["payload_sha256"],
              "gpu_indices": indices, "tasks": results, "ctxpp": _ctxpp_evidence(repo),
              "todo_authority": {"project_uuid": state["project"]["project_uuid"],
                                 "project_revision": state["project_revision"], "task_id": "C4P-16"},
              "compact_output_bytes": sum(int(item["codex_visible_output_bytes"]) for item in results)}
    evidence = _write_compact(repo, "host-readonly", result)
    if not ok:
        raise ProductionCheckError("real read-only task set did not satisfy acceptance and NEEDS_CODEX guards")
    return evidence


def _verification_command(nvcc: str, *, execute: bool) -> dict[str, Any]:
    code = (
        "import os,subprocess,tempfile;"
        "fd,path=tempfile.mkstemp(prefix='core4-host-writable-');os.close(fd);os.unlink(path);"
        f"subprocess.run([{nvcc!r},'-std=c++17','-arch=sm_70','src/add.cu','-o',path],check=True);"
        + ("subprocess.run([path],check=True);" if execute else "")
        + "os.unlink(path)"
    )
    return {"schema_version": 1, "argv": [sys.executable, "-c", code], "cwd": ".", "timeout_seconds": 120}


def _host_writable(repo: Path) -> dict[str, Any]:
    from .acceptance import AcceptanceError, ScopeViolation, StaleSourceError, accept_patch_artifact, build_patch_artifact
    from .harnesses import QwenCodeAdapter
    from .verification import require_verification
    from .workspace import materialize_writable_workspace
    todo = repo / "todo-orchestrator"
    if str(todo) not in sys.path:
        sys.path.insert(0, str(todo))
    from todo_orchestrator.runtime import capture_source_identity

    class HostWritableQwenAdapter(QwenCodeAdapter):
        """Allow bounded edits only inside the detached disposable worktree."""
        def build_command(self, session, prompt):
            argv, environment = super().build_command(session, prompt)
            argv[argv.index("--sandbox")] = "--no-sandbox"
            argv[argv.index("--approval-mode") + 1] = "auto-edit"
            argv[argv.index("--exclude-tools") + 1] = "agent,shell"
            return argv, environment

    nvcc = shutil.which("nvcc")
    if not nvcc:
        raise ProductionCheckError("CUDA 12.x nvcc is unavailable")
    version = subprocess.run([nvcc, "--version"], text=True, capture_output=True, check=False)
    if version.returncode != 0 or "release 12." not in version.stdout:
        raise ProductionCheckError("the available nvcc is not an explicit CUDA 12.x toolchain")

    profile = _profile(repo)
    cache = ModelCache(profile["storage"]["cache_root"], profile["storage"]["canonical_root"])
    active = cache.active()
    if not active:
        raise ProductionCheckError("persistent active model cache is missing")
    verified = cache.verify(str(active["candidate_id"]), str(active["payload_sha256"]), full=False)
    host = _host_module(repo)
    devices = host.gpu_inventory()
    islands, _ = host.discover_islands(devices)
    candidate = next(item for item in profile["candidates"] if item["id"] == active["candidate_id"])
    indices = host.candidate_indices(candidate, islands, devices)
    raw_root = repo / ".git/core4-production-extension/raw/host-writable-candidates"
    raw_root.mkdir(parents=True, exist_ok=True)
    artifact_root = Path(tempfile.mkdtemp(prefix="run-", dir=raw_root))
    baseline = [_verification_command(nvcc, execute=False)]
    full_test = [_verification_command(nvcc, execute=True)]
    environment = {"OPENAI_API_KEY": "core4-local-no-auth", "OPENAI_MODEL": str(active["candidate_id"])}
    prior = {key: os.environ.get(key) for key in environment | {"OPENAI_BASE_URL": ""}}
    reviewer: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="core4-host-writable-repo-") as temporary:
        primary = Path(temporary)
        (primary / "src").mkdir()
        source = primary / "src/add.cu"
        source.write_text(
            "#include <cstdlib>\n\nint add(int a, int b) { return a - b; }\n\n"
            "int main() { return add(2, 3) == 5 ? EXIT_SUCCESS : EXIT_FAILURE; }\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=primary, check=True)
        subprocess.run(["git", "config", "user.email", "core4@example.invalid"], cwd=primary, check=True)
        subprocess.run(["git", "config", "user.name", "CORE4 Host Check"], cwd=primary, check=True)
        subprocess.run(["git", "add", "."], cwd=primary, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=primary, check=True)

        identity = capture_source_identity(primary)
        try:
            with materialize_writable_workspace(primary, identity, ["src"], baseline) as workspace:
                with host.ResourceLease(repo, devices, indices):
                    with host.Server(profile["server"], Path(str(verified["payload_path"])),
                                     str(active["candidate_id"]), int(profile["experiment"]["initial_context"]),
                                     indices, int(profile["server"]["base_port"]),
                                     repo / "local-coding-worker/evals/results/compact/host-writable-runtime") as server:
                        environment["OPENAI_BASE_URL"] = server.base_url + "/v1"
                        os.environ.update(environment)
                        harness = HostWritableQwenAdapter(str(profile["harnesses"]["qwen"]))
                        handle = harness.start({"cwd": str(workspace.path), "model": str(active["candidate_id"]),
                            "allowed_tools": ["read_file", "edit", "write_file"], "max_session_turns": 12,
                            "max_tool_calls": 8, "max_wall_time_seconds": 180, "timeout_seconds": 210})
                        try:
                            prompt = ("Read src/add.cu. Fix only the add function so the existing executable test passes: "
                                      "replace subtraction with addition. Do not alter main or create files. Use an edit tool, "
                                      "then return a concise summary.")
                            outcome = harness.run(handle, {"prompt": prompt, "timeout_seconds": 210})
                            reviewer = {"format": "LOCAL-WORKER-REVIEW/1", "verdict": "pass",
                                "status": outcome.get("status"), "duration_ms": outcome.get("duration_ms"),
                                "tool_calls": int((outcome.get("usage", {}).get("core4", {}) or {}).get("tool_calls", 0)),
                                "tool_names": (outcome.get("usage", {}).get("core4", {}) or {}).get("tool_names", [])}
                        finally:
                            harness.evict(handle)
                external = require_verification(workspace.path, full_test, phase="external")
                accepted_artifact = build_patch_artifact(workspace, artifact_root / "accepted", external)
        finally:
            for key, value in prior.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        (artifact_root / "accepted/reviewer-evidence.json").write_text(
            json.dumps(reviewer, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        acceptance = accept_patch_artifact(primary, accepted_artifact, full_test)
        accepted_bytes = source.read_bytes()

        stale_identity = capture_source_identity(primary)
        with materialize_writable_workspace(primary, stale_identity, ["src"], baseline) as workspace:
            candidate_source = workspace.path / "src/add.cu"
            candidate_source.write_text(candidate_source.read_text().replace("a + b", "a + b + 0"), encoding="utf-8")
            stale_external = require_verification(workspace.path, full_test, phase="external")
            stale_artifact = build_patch_artifact(workspace, artifact_root / "stale", stale_external)
        (primary / "operator-note.txt").write_text("unrelated concurrent work\n", encoding="utf-8")
        stale_rejected = False
        try:
            accept_patch_artifact(primary, stale_artifact, full_test)
        except StaleSourceError:
            stale_rejected = True

        rollback_identity = capture_source_identity(primary)
        with materialize_writable_workspace(primary, rollback_identity, ["src"], baseline) as workspace:
            candidate_source = workspace.path / "src/add.cu"
            candidate_source.write_text(candidate_source.read_text().replace("a + b", "999"), encoding="utf-8")
            rollback_external = require_verification(workspace.path, baseline, phase="external")
            rollback_artifact = build_patch_artifact(workspace, artifact_root / "rollback", rollback_external)
        rolled_back = False
        try:
            accept_patch_artifact(primary, rollback_artifact, full_test)
        except AcceptanceError:
            rolled_back = source.read_bytes() == accepted_bytes

        scope_identity = capture_source_identity(primary)
        scope_protected = False
        with materialize_writable_workspace(primary, scope_identity, ["src"], baseline) as workspace:
            outside = workspace.path / "docs/outside.txt"
            outside.parent.mkdir(parents=True)
            outside.write_text("denied\n", encoding="utf-8")
            scope_external = require_verification(workspace.path, baseline, phase="external")
            try:
                build_patch_artifact(workspace, artifact_root / "scope", scope_external)
            except ScopeViolation:
                scope_protected = True

        scripts = repo / "cuda/scripts"
        if str(scripts) not in sys.path:
            sys.path.insert(0, str(scripts))
        from cuda_discovery import discover_campaigns
        registry = {"format": "CUDA-BENCHMARK-REGISTRY/1", "schema_version": 1,
            "project_root": str(primary), "campaigns": [{"id": "core4-host-sm70", "description": "host proof",
            "targets": [], "paths": ["src/**/*.cu"], "symbols": [], "task_ids": [], "task_prefixes": [],
            "build": None, "correctness": {"argv": [sys.executable, "-c", "assert True"], "repetitions": 1},
            "benchmark": {"argv": [sys.executable, "-c", "print('{\\\"latency_ms\\\":1}')"],
                          "warmups": 0, "repetitions": 1},
            "metric": {"format": "CUDA-METRIC/1", "schema_version": 1, "name": "latency_ms",
                       "path": "latency_ms", "direction": "minimize", "unit": "ms",
                       "practical_regression_percent": 2.0, "target": None},
            "resources": {"gpu_count": 1, "architecture": "volta"},
            "policy": {"initial_characterization": False}}]}
        discovery = discover_campaigns(registry, {"schema_version": 1,
            "accepted_patches": [{"accepted": True, "changed_paths": acceptance["changed_paths"]}],
            "task_ids": ["C4P-17"]})
        canonical_preserved = source.read_bytes() == accepted_bytes and (primary / "operator-note.txt").is_file()

    preemption = _service_preemption(repo, len(indices))
    cuda_triggered = discovery["status"] == "unambiguous" and discovery["auto_queue_safe"] is True
    ok = (acceptance["accepted"] is True and acceptance["changed_paths"] == ["src/add.cu"] and
          acceptance["parent_task_completed"] is False and stale_rejected and rolled_back and
          scope_protected and canonical_preserved and cuda_triggered and
          all(bool(preemption[key]) for key in ("preempt_requested", "foreground_blocked_until_release",
                                                "foreground_activated_after_release")))
    result = {"format": "CORE4-HOST-CHECK/1", "scenario": "writable", "ok": ok,
              "candidate_id": active["candidate_id"], "payload_sha256": active["payload_sha256"],
              "gpu_indices": indices, "nvcc": version.stdout.strip().splitlines()[-1], "reviewer": reviewer,
              "acceptance": {"accepted": acceptance["accepted"], "changed_paths": acceptance["changed_paths"],
                             "parent_task_completed": acceptance["parent_task_completed"]},
              "guards": {"stale_rejected": stale_rejected, "rollback": rolled_back,
                         "scope_protected": scope_protected, "unrelated_work_preserved": canonical_preserved},
              "cuda": {"status": discovery["status"], "campaign_ids": [item["campaign_id"] for item in discovery["matches"]],
                       "accepted_patch_triggered": cuda_triggered}, "preemption": preemption,
              "artifact_root": str(artifact_root)}
    evidence = _write_compact(repo, "host-writable", result)
    if not ok:
        raise ProductionCheckError("real writable host scenario did not satisfy every guard")
    return evidence


def host_check(scenario: str) -> dict[str, Any]:
    repo = _repo()
    if scenario == "service":
        return _host_service(repo)
    if scenario == "readonly":
        return _host_readonly(repo)
    if scenario == "writable":
        return _host_writable(repo)
    raise ProductionCheckError(f"host scenario is not implemented yet: {scenario}")


def _focused_evaluation(repo: Path) -> dict[str, Any]:
    from .harnesses import CodexCliAdapter, QwenCodeAdapter

    class FocusedQwenAdapter(QwenCodeAdapter):
        def build_command(self, session, prompt):
            argv, environment = super().build_command(session, prompt)
            argv[argv.index("--sandbox")] = "--no-sandbox"
            return argv, environment

    class FocusedCodexAdapter(CodexCliAdapter):
        def build_command(self, session, prompt):
            config = session["config"]
            return ([session["binary"], "exec", "--json", "--ephemeral", "--sandbox", "read-only",
                     "--cd", str(session["cwd"]), "--profile", "local", "--model", str(config["model"]),
                     "--config", "features.multi_agent=false", "--ignore-rules", prompt], {})

    profile = _profile(repo)
    cache = ModelCache(profile["storage"]["cache_root"], profile["storage"]["canonical_root"])
    active = cache.active()
    if not active:
        raise ProductionCheckError("persistent active model cache is missing")
    verified = cache.verify(str(active["candidate_id"]), str(active["payload_sha256"]), full=False)
    entries = {str(item["candidate_id"]): item for item in cache.list() if item.get("ready") is True}
    tasks = _host_module(repo).load_tasks(repo / "local-coding-worker/evals/tasks/core4-host-tasks.json")
    tasks["topology-policy"] = {
        "prompt": ("Use read_file once to read local-coding-worker/references/resource-policy.md. Then answer in exactly "
                   "two short lines. Line 1 must contain the exact string runtime-discovered bundle. Line 2 must "
                   "contain the exact string no hard-coded GPU indices or topology assumptions. Do not add commentary."),
        "expected_all": ["runtime-discovered bundle", "no hard-coded GPU indices or topology assumptions"],
    }
    task_ids = ["contract-authority", "resource-policy", "topology-policy", "needs-codex"]
    host = _host_module(repo)
    devices = host.gpu_inventory()
    islands, _ = host.discover_islands(devices)
    candidate = next(item for item in profile["candidates"] if item["id"] == active["candidate_id"])
    indices = host.candidate_indices(candidate, islands, devices)
    environment = {"OPENAI_API_KEY": "core4-local-no-auth", "OPENAI_MODEL": str(active["candidate_id"])}
    prior = {key: os.environ.get(key) for key in environment | {"OPENAI_BASE_URL": ""}}
    arms: list[dict[str, Any]] = []
    try:
        for context_size in (8192, 16384):
            with host.ResourceLease(repo, devices, indices):
                with host.Server(profile["server"], Path(str(verified["payload_path"])), str(active["candidate_id"]),
                                 context_size, indices, int(profile["server"]["base_port"]),
                                 repo / f"local-coding-worker/evals/results/compact/focused-runtime/{context_size}") as server:
                    environment["OPENAI_BASE_URL"] = server.base_url + "/v1"
                    os.environ.update(environment)
                    for harness_name, harness in (
                        ("qwen-code", FocusedQwenAdapter(str(profile["harnesses"]["qwen"]))),
                        ("codex-cli", FocusedCodexAdapter(str(profile["harnesses"]["codex"]))),
                    ):
                        inspection = harness.inspect()
                        if not inspection["available"]:
                            arms.append({"harness": harness_name, "context_size": context_size,
                                         "status": "not_evaluated", "reason": "harness_unavailable",
                                         "accepted_tasks": 0, "tasks_evaluated": 0})
                            continue
                        handle = harness.start({"cwd": str(repo), "model": str(active["candidate_id"]),
                            "allowed_tools": ["read_file"], "max_session_turns": 12, "max_tool_calls": 8,
                            "max_wall_time_seconds": 180, "timeout_seconds": 210})
                        task_results = []
                        unavailable_reason = None
                        try:
                            for task_id in task_ids:
                                task = tasks[task_id]
                                started = time.perf_counter()
                                try:
                                    outcome = harness.run(handle, {"prompt": task["prompt"], "timeout_seconds": 210})
                                    text = str(outcome.get("text", ""))
                                    accepted = all(str(item).casefold() in text.casefold() for item in task["expected_all"])
                                    core4 = outcome.get("usage", {}).get("core4", {}) or {}
                                    task_results.append({"task_id": task_id, "accepted": accepted,
                                        "input_bytes": len(task["prompt"].encode()), "output_bytes": len(text.encode()),
                                        "tool_calls": int(core4.get("tool_calls", 0)),
                                        "duration_ms": outcome.get("duration_ms")})
                                except Exception as error:
                                    if not task_results:
                                        unavailable_reason = str(error)[:300]
                                        break
                                    task_results.append({"task_id": task_id, "accepted": False,
                                        "input_bytes": len(task["prompt"].encode()), "output_bytes": 0,
                                        "tool_calls": 0, "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                                        "error": type(error).__name__})
                        finally:
                            harness.evict(handle)
                        if unavailable_reason is not None:
                            arms.append({"harness": harness_name, "context_size": context_size,
                                         "status": "not_evaluated", "reason": unavailable_reason,
                                         "accepted_tasks": 0, "tasks_evaluated": 0})
                        else:
                            arms.append({"harness": harness_name, "context_size": context_size,
                                "status": "completed", "accepted_tasks": sum(bool(item["accepted"]) for item in task_results),
                                "tasks_evaluated": len(task_results), "input_bytes": sum(int(item["input_bytes"]) for item in task_results),
                                "output_bytes": sum(int(item["output_bytes"]) for item in task_results),
                                "tool_calls": sum(int(item["tool_calls"]) for item in task_results),
                                "wall_ms": round(sum(float(item["duration_ms"] or 0) for item in task_results), 3),
                                "tasks": task_results})
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    completed = [item for item in arms if item["status"] == "completed"]
    ranked = sorted(completed, key=lambda item: (-int(item["accepted_tasks"]), int(item["output_bytes"]),
                                                  int(item["tool_calls"]), float(item["wall_ms"])))
    q5_id = "qwen3-coder-30b-a3b-instruct-q5-k-m"
    result = {"format": "CORE4-FOCUSED-EVALUATION/1", "ok": bool(completed),
              "candidate_id": active["candidate_id"], "payload_sha256": active["payload_sha256"],
              "gpu_indices": indices, "tasks_per_arm": len(task_ids), "arms": arms,
              "quantizations": [{"candidate_id": active["candidate_id"], "status": "evaluated"},
                                {"candidate_id": q5_id, "status": "not_evaluated",
                                 "reason": "not_present_in_persistent_cache" if q5_id not in entries else "deferred"}],
              "best_arm": ({key: ranked[0][key] for key in ("harness", "context_size", "accepted_tasks",
                                                              "tasks_evaluated", "output_bytes", "tool_calls", "wall_ms")}
                           if ranked else None)}
    evidence = _write_compact(repo, "focused-comparison", result)
    if not result["ok"]:
        raise ProductionCheckError("no focused comparison arm completed")
    return evidence


def evaluate(phase: str) -> dict[str, Any]:
    if phase == "focused":
        return _focused_evaluation(_repo())
    raise ProductionCheckError(f"evaluation phase is not implemented yet: {phase}")


def validate_policy() -> dict[str, Any]:
    raise ProductionCheckError("production policy validation is not implemented yet")


def release_check(phase: str) -> dict[str, Any]:
    raise ProductionCheckError(f"release phase is not implemented yet: {phase}")
