from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any


ROLES = {"explain", "debug", "review", "test_plan"}
INTENTS = {"understand", "debug", "test", "api", "performance"}
REQUEST_KEYS = {
    "format", "schema_version", "backend", "role", "readonly", "repo_root",
    "child_token", "objective", "scopes", "target", "intent",
    "budget_tokens", "max_items",
}
REQUEST_V2_KEYS = REQUEST_KEYS | {"execution"}


class WorkerError(RuntimeError):
    pass


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise WorkerError("scopes must be non-empty repository-relative paths")
    path = PurePosixPath(value.replace("\\", "/"))
    normalized = str(path)
    if path.is_absolute() or normalized in {".", ".."} or ".." in path.parts:
        raise WorkerError(f"scope is not repository-relative: {value!r}")
    return normalized


def normalize_request(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkerError("request must be a JSON object")
    version = value.get("schema_version")
    keys = REQUEST_V2_KEYS if version == 2 else REQUEST_KEYS
    extra = sorted(set(value) - keys)
    missing = sorted(keys - set(value))
    if extra or missing:
        raise WorkerError(f"request fields invalid: missing={missing} extra={extra}")
    if version not in {1, 2} or value.get("format") != f"LCW-REQUEST/{version}":
        raise WorkerError("request format must be LCW-REQUEST/1 or LCW-REQUEST/2")
    if value["backend"] not in ({"fake"} if version == 1 else {"fake", "real"}):
        raise WorkerError("request backend is unsupported for its version")
    if value["role"] not in ROLES or value["intent"] not in INTENTS:
        raise WorkerError("unsupported read-only role or ctxpp intent")
    if value["readonly"] is not True:
        raise WorkerError("CORE4 read-only MVP requires readonly=true")
    if not isinstance(value["child_token"], str) or not value["child_token"].startswith("toch_"):
        raise WorkerError("a restricted todo child token is required")
    for key, limit in (("objective", 500), ("target", 300)):
        if not isinstance(value[key], str) or not value[key].strip() or len(value[key]) > limit:
            raise WorkerError(f"{key} must contain 1-{limit} characters")
    if not isinstance(value["repo_root"], str) or not value["repo_root"]:
        raise WorkerError("repo_root must be a non-empty path")
    root = Path(value["repo_root"]).resolve()
    if not root.is_dir():
        raise WorkerError(f"repo_root does not exist: {root}")
    scopes = value["scopes"]
    if not isinstance(scopes, list) or not 1 <= len(scopes) <= 16:
        raise WorkerError("scopes must contain 1-16 paths")
    normalized_scopes = sorted({_relative(item) for item in scopes})
    for scope in normalized_scopes:
        path = root / scope
        if not path.exists() or path.is_symlink():
            raise WorkerError(f"scope must exist and may not be a symlink: {scope}")
    budget = value["budget_tokens"]
    max_items = value["max_items"]
    if isinstance(budget, bool) or not isinstance(budget, int) or not 256 <= budget <= 12000:
        raise WorkerError("budget_tokens must be between 256 and 12000")
    if isinstance(max_items, bool) or not isinstance(max_items, int) or not 1 <= max_items <= 32:
        raise WorkerError("max_items must be between 1 and 32")
    result = dict(value)
    result["repo_root"] = str(root)
    result["scopes"] = normalized_scopes
    if version == 2:
        execution = value.get("execution")
        if not isinstance(execution, dict):
            raise WorkerError("execution must be an object")
        if set(execution) - {"backend", "harness", "gpu_count", "service_profile", "harness_config"}:
            raise WorkerError("execution contains unknown fields")
        if execution.get("backend") != value["backend"]:
            raise WorkerError("execution backend must match request backend")
        if execution.get("harness", "qwen") not in {"qwen", "codex"}:
            raise WorkerError("execution harness must be qwen or codex")
        count = execution.get("gpu_count", 1)
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 16:
            raise WorkerError("execution gpu_count must be between 1 and 16")
    return result


def eligibility(request: object) -> dict[str, Any]:
    try:
        normalized = normalize_request(request)
    except WorkerError as error:
        return {"format": "LCW-ELIGIBILITY/1", "eligible": False, "reasons": [str(error)]}
    return {
        "format": "LCW-ELIGIBILITY/1",
        "eligible": True,
        "reasons": [],
        "role": normalized["role"],
        "backend": normalized["backend"],
        "readonly": True,
    }


def _run_json(command: list[str], cwd: Path) -> dict[str, Any]:
    process = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        detail = process.stderr.strip() or process.stdout.strip()
        raise WorkerError(f"command failed ({process.returncode}): {detail[:500]}")
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError as error:
        raise WorkerError("command did not return JSON") from error
    if isinstance(value, dict) and value.get("ok") is True and isinstance(value.get("data"), dict):
        return value["data"]
    if not isinstance(value, dict):
        raise WorkerError("command JSON must be an object")
    return value


def _inside(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope + "/")


class ReadOnlySnapshot:
    def __init__(self, repo_root: Path, scopes: list[str]):
        self.repo_root = repo_root
        self.scopes = scopes
        self._temp: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None
        self.paths = 0

    def __enter__(self) -> "ReadOnlySnapshot":
        self._temp = tempfile.TemporaryDirectory(prefix="local-worker-readonly-")
        self.root = Path(self._temp.name) / "repo"
        self.root.mkdir()
        for scope in self.scopes:
            source = self.repo_root / scope
            destination = self.root / scope
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source.is_dir():
                if any(path.is_symlink() for path in source.rglob("*")):
                    raise WorkerError(f"scope contains a symlink: {scope}")
                shutil.copytree(source, destination, symlinks=False)
            else:
                shutil.copy2(source, destination)
        for path in sorted(self.root.rglob("*"), reverse=True):
            if path.is_symlink():
                raise WorkerError("snapshot contains a symlink")
            mode = path.stat().st_mode
            path.chmod(mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
            self.paths += 1
        self.root.chmod(self.root.stat().st_mode & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH))
        self.paths += 1
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.root and self.root.exists():
            for path in [self.root, *self.root.rglob("*")]:
                try:
                    path.chmod(path.stat().st_mode | stat.S_IWUSR)
                except OSError:
                    pass
        if self._temp:
            self._temp.cleanup()


def _fake_backend(request: dict[str, Any], packet: dict[str, Any], snapshot: ReadOnlySnapshot) -> dict[str, Any]:
    if snapshot.root is None:
        raise WorkerError("read-only snapshot was not initialized")
    target = packet.get("target") or next(iter(packet.get("canonical_targets", [])), {})
    location = target.get("location", {})
    target_path = str(location.get("path", ""))
    if not target_path or not any(_inside(target_path, scope) for scope in request["scopes"]):
        return {"status": "needs_codex", "summary": "Target is outside the authorized snapshot scopes.", "findings": []}
    copied_target = snapshot.root / target_path
    expected_hash = str(location.get("content_sha256", ""))
    if not copied_target.is_file() or hashlib.sha256(copied_target.read_bytes()).hexdigest() != expected_hash:
        return {"status": "needs_codex", "summary": "Snapshot target does not match the ctxpp packet source hash.", "findings": []}
    writable = [path for path in [snapshot.root, *snapshot.root.rglob("*")] if path.stat().st_mode & 0o222]
    if writable:
        raise WorkerError("read-only snapshot contains writable paths")
    trust = packet.get("trust", {})
    coverage = packet.get("coverage", {})
    sufficient = ((trust.get("target_range") == "hash-verified"
                   and trust.get("relationships") == "semantic"
                   and not trust.get("index_incomplete", True)
                   and coverage.get("sufficient") is True)
                  or (request["schema_version"] == 2
                      and request["role"] in trust.get("sufficient_for", [])
                      and not trust.get("missing_required")
                      and packet.get("budget_exceeded") is False))
    if not sufficient:
        return {
            "status": "needs_codex",
            "summary": "NEEDS_CODEX: packet trust or coverage is insufficient for bounded local judgment.",
            "findings": [f"Inspect canonical target {target_path} and requested expansion handles."],
        }
    return {
        "status": "no_change",
        "summary": f"Read-only {request['role']} completed against a hash-verified packet.",
        "findings": [
            f"Target: {target['name']}",
            f"Canonical range: {target_path}:{location.get('line')}-{location.get('end_line')}",
            "Snapshot exposed no writable paths.",
        ],
    }


def run_controller(request_value: object, *, production_runtime: object | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    request = normalize_request(request_value)
    root = Path(request["repo_root"])
    skill_root = Path(__file__).resolve().parents[1]
    repo_skills = skill_root.parent
    todo_cli = Path(os.environ.get("LCW_TODO_CLI", repo_skills / "todo-orchestrator/scripts/todo.py"))
    ctxpp_cli = Path(os.environ.get("LCW_CTXPP_CLI", repo_skills / "cpp-context-compiler/scripts/ctxpp"))
    _run_json([
        sys.executable, str(todo_cli), "child", "heartbeat", "--repo-root", str(root),
        "--child-token", request["child_token"], "--lease-seconds", "300", "--json",
    ], root)
    if request["schema_version"] == 2:
        task_spec = json.dumps({"objective": request["objective"], "role": request["role"],
            "read_paths": request["scopes"], "write_paths": [], "forbidden_paths": [],
            "target_symbols": [request["target"]], "failing_tests": [], "interface_ids": [],
            "acceptance_gates": []}, separators=(",", ":"))
        packet_argv = [str(ctxpp_cli), "--root", str(root), "--json", "packet", "--task-spec", task_spec,
                       "--consumer", "local-worker", "--budget", str(request["budget_tokens"]),
                       "--max-items", str(request["max_items"])]
    else:
        packet_argv = [str(ctxpp_cli), "--root", str(root), "--json", "packet", request["target"],
                       "--intent", request["intent"], "--budget", str(request["budget_tokens"]),
                       "--max-items", str(request["max_items"])]
    packet = _run_json(packet_argv, root)
    if packet.get("format") not in {"CTXPP-CONTEXT-PACKET/1", "CTXPP-CONTEXT-PACKET/2"} or packet.get("readonly") is not True:
        raise WorkerError("ctxpp did not return a read-only context packet")
    with ReadOnlySnapshot(root, request["scopes"]) as snapshot:
        if request["backend"] == "fake":
            backend = _fake_backend(request, packet, snapshot)
        else:
            if production_runtime is None:
                skill_root = Path(__file__).resolve().parents[1]
                if str(skill_root) not in sys.path:
                    sys.path.insert(0, str(skill_root))
                from local_worker.controller import ProductionReadOnlyRuntime
                production_runtime = ProductionReadOnlyRuntime()
            execute = getattr(production_runtime, "execute", None)
            if not callable(execute):
                raise WorkerError("production runtime must implement execute")
            backend = execute(request, packet, snapshot)
            if not isinstance(backend, dict):
                raise WorkerError("production runtime result must be an object")
        snapshot_paths = snapshot.paths
    status = str(backend["status"])
    if status not in {"completed", "no_change", "needs_codex", "failed", "preempted"}:
        raise WorkerError("worker backend returned an unsupported status")
    todo_status = "needs_codex" if status in {"needs_codex", "preempted"} else "failed" if status == "failed" else "succeeded"
    _run_json([
        sys.executable, str(todo_cli), "child", "report", "--repo-root", str(root),
        "--child-token", request["child_token"], "--status", todo_status,
        "--summary", str(backend["summary"])[:500], "--json",
    ], root)
    return {
        "format": f"LOCAL-CODING-WORKER-RESULT/{request['schema_version']}",
        "schema_version": request["schema_version"],
        "status": status,
        "role": request["role"],
        "summary": str(backend["summary"])[:500],
        "findings": [str(item)[:500] for item in backend.get("findings", [])[:16]],
        "changed_paths": [],
        "packet_hash": packet.get("packet_hash"),
        "source_identity": packet.get("source_identity"),
        "telemetry": {
            "backend_calls": 1,
            "tool_calls": int(backend.get("tool_calls", 3)),
            "packet_tokens": int(packet.get("estimated_tokens", 0)),
            "snapshot_paths": snapshot_paths,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        },
        "child_reported": True,
        **({"backend": request["backend"], "artifacts": list(backend.get("artifacts", []))}
           if request["schema_version"] == 2 else {}),
    }
