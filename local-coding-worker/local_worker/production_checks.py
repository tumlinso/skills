"""Bounded real-host checks and compact production evidence for CORE4."""

from __future__ import annotations

import importlib.util
import json
import sys
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


def host_check(scenario: str) -> dict[str, Any]:
    repo = _repo()
    if scenario == "service":
        return _host_service(repo)
    raise ProductionCheckError(f"host scenario is not implemented yet: {scenario}")


def evaluate(phase: str) -> dict[str, Any]:
    raise ProductionCheckError(f"evaluation phase is not implemented yet: {phase}")


def validate_policy() -> dict[str, Any]:
    raise ProductionCheckError("production policy validation is not implemented yet")


def release_check(phase: str) -> dict[str, Any]:
    raise ProductionCheckError(f"release phase is not implemented yet: {phase}")
