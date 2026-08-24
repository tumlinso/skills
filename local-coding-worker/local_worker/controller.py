"""CORE4 integration controller over frozen public skill interfaces."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path, PurePosixPath
from typing import Any, Callable
import uuid

from .acceptance import AcceptanceError, StaleSourceError, accept_patch_artifact, build_patch_artifact
from .verification import require_verification
from .workspace import materialize_writable_workspace, normalize_scopes


class IntegrationError(RuntimeError):
    pass


def _qwen_budget_config(profile: dict[str, Any], *, writable: bool) -> dict[str, int]:
    harness = profile.get("harnesses", {})
    tool_key = "qwen_writable_max_tool_calls" if writable else "qwen_readonly_max_tool_calls"
    default_tools = 8 if writable else 6
    return {
        "max_session_turns": int(harness.get("qwen_max_session_turns", 0)),
        "max_tool_calls": int(harness.get(tool_key, harness.get("qwen_max_tool_calls", default_tools))),
        "structured_retry_margin": int(harness.get("qwen_structured_retry_margin", 2)),
        "max_wall_time_seconds": int(harness.get("qwen_max_wall_time_seconds", 180)),
    }


class ProductionReadOnlyRuntime:
    """Compose frozen production interfaces; inject fakes for software-only proof."""

    def __init__(self, *, profile: dict[str, Any] | None = None, cache: Any = None,
                 runtime: Any = None, service: Any = None, supervisor: Any = None,
                 harness_factory: Callable[[str], Any] | None = None) -> None:
        self._profile, self._cache, self._runtime, self._service = profile, cache, runtime, service
        self._supervisor = supervisor
        self._harness_factory = harness_factory

    def _components(self, root: Path) -> tuple[dict[str, Any], Any]:
        import tomllib
        from .supervisor import SupervisorClient
        profile = self._profile or tomllib.loads((Path(__file__).resolve().parents[1] / "config/production-profile.toml").read_text(encoding="utf-8"))
        return profile, self._supervisor or SupervisorClient(root)

    def execute(self, request: dict[str, Any], packet: dict[str, Any], snapshot: Any) -> dict[str, Any]:
        from .harnesses import CodexCliAdapter, QwenCodeAdapter
        root = Path(request["repo_root"])
        profile, supervisor = self._components(root)
        deployment = profile.get("deployment_policy", {})
        if deployment.get("real_local_enabled") is not True:
            return {"status": "needs_codex", "summary": str(deployment.get("reason", "real local execution disabled")),
                    "findings": [], "tool_calls": 0, "artifacts": []}
        execution = request["execution"]
        harness_name = str(execution.get("harness", "qwen"))
        harness = (self._harness_factory(harness_name) if self._harness_factory else
                   QwenCodeAdapter(str(profile["harnesses"]["qwen"])) if harness_name == "qwen" else
                   CodexCliAdapter(str(profile["harnesses"]["codex"])))
        endpoint = None
        harness_handle = None
        task_runtime = None
        try:
            admission_id = execution.get("admission_id")
            endpoint = supervisor.request("warm", **({"admission_id": admission_id} if admission_id else {}))
            task_runtime = tempfile.TemporaryDirectory(prefix="core4-qwen-task-")
            harness_config = {
                **dict(execution.get("harness_config") or {}),
                **_qwen_budget_config(profile, writable=False),
                "cwd": str(snapshot.root), "repository_root": str(snapshot.root),
                "authorized_read_paths": list(request["scopes"]), "mode": "readonly",
                "base_url": endpoint["base_url"], "model": endpoint["model_id"],
                "runtime_dir": task_runtime.name,
            }
            harness_handle = harness.start(harness_config)
            result = harness.run(harness_handle, {"prompt": json.dumps({
                "objective": request["objective"], "role": request["role"],
                "authorized_roots": request["scopes"], "packet": packet,
                "output_contract": "CORE4-MODEL-OUTCOME/1",
                "escalate_when": "Evidence is insufficient, scope is inadequate, or an architectural decision is required.",
                "constraints": ("Every evidence path must be repository-relative within the isolated snapshot, never absolute. "
                                "This is read-only work, so changed_paths must be an empty array."),
            }, separators=(",", ":"))})
            status = "completed" if result.get("status") == "succeeded" else str(result.get("status", "failed"))
            artifact = {
                "kind": "harness-summary", "harness": harness_name,
                "model_sha256": endpoint["model_sha256"], "usage": result.get("usage", {}),
                "duration_ms": result.get("duration_ms"), "slot_id": endpoint.get("slot_id"),
                "service_lease_id": endpoint.get("service_lease_id"),
                "server_pid": endpoint.get("server_pid"), "gpu_uuids": endpoint.get("gpu_uuids", []),
                "reused": endpoint.get("reused"), "qwen_runtime_directory": task_runtime.name,
            }
            model_outcome = result.get("model_outcome") if isinstance(result.get("model_outcome"), dict) else None
            return {"status": status, "summary": str((model_outcome or {}).get("summary") or result.get("reason") or status)[:500],
                    "findings": [], "tool_calls": int(result.get("usage", {}).get("core4", {}).get("tool_calls", 0)),
                    "artifacts": [artifact], "model_outcome": model_outcome}
        except Exception as error:
            reason = str(error)[:500]
            preempted = False
            if endpoint and endpoint.get("service_lease_id"):
                try:
                    preempted = bool(supervisor.request(
                        "preemption-status", service_lease_id=endpoint["service_lease_id"]
                    ).get("preempt_requested"))
                except Exception:
                    pass
            retryable = preempted or "resource_unavailable" in reason
            return {"status": "needs_codex" if retryable else "failed",
                    "summary": "resource_preempted" if preempted else reason,
                    "retryable": retryable, "findings": [], "tool_calls": 0, "artifacts": []}
        finally:
            if harness_handle is not None: harness.evict(harness_handle)
            if endpoint is not None:
                try:
                    supervisor.request("release", service_lease_id=endpoint.get("service_lease_id"))
                except Exception:
                    pass
            if task_runtime is not None:
                task_runtime.cleanup()


def _runtime_source():
    skills_root = Path(__file__).resolve().parents[2]
    todo_root = skills_root / "todo-orchestrator"
    if str(todo_root) not in sys.path:
        sys.path.insert(0, str(todo_root))
    from todo_orchestrator.runtime import capture_source_identity
    return capture_source_identity


def _inside(path: str, scope: str) -> bool:
    return path == scope or path.startswith(scope + "/")


def _relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise IntegrationError("changed paths must be non-empty strings")
    path = PurePosixPath(value.replace("\\", "/"))
    normalized = str(path)
    if path.is_absolute() or normalized in {".", ".."} or ".." in path.parts:
        raise IntegrationError(f"changed path is not repository-relative: {value!r}")
    return normalized


def _object(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise IntegrationError(f"{name} must be an object")
    return dict(value)


def _scope_state(root: Path, scopes: list[str]) -> dict[str, str]:
    """Hash only source paths relevant to one delegated task."""
    state: dict[str, str] = {}
    for scope in sorted(set(scopes)):
        candidate = root / scope
        paths = [candidate] if candidate.is_file() or candidate.is_symlink() else (
            sorted(path for path in candidate.rglob("*") if path.is_file() or path.is_symlink())
            if candidate.is_dir() else []
        )
        for path in paths:
            relative = path.relative_to(root).as_posix()
            payload = (b"symlink\0" + os.readlink(path).encode()) if path.is_symlink() else path.read_bytes()
            state[relative] = hashlib.sha256(payload).hexdigest()
    return state


class _ControllerAcceptanceLock:
    def __init__(self, root: Path):
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=root, text=True,
                                capture_output=True, check=True).stdout.strip()
        common_path = Path(common) if Path(common).is_absolute() else root / common
        lock_root = common_path.resolve() / "local-coding-worker/locks"
        lock_root.mkdir(parents=True, exist_ok=True)
        self.stream = (lock_root / "controller-acceptance.lock").open("a+b")

    def __enter__(self):
        fcntl.flock(self.stream.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, traceback):
        fcntl.flock(self.stream.fileno(), fcntl.LOCK_UN)
        self.stream.close()


class IntegrationController:
    """One bounded child flow; todo and canonical source retain authority."""

    def __init__(
        self,
        *,
        todo_cli: str | Path | None = None,
        ctxpp_cli: str | Path | None = None,
        worker_cli: str | Path | None = None,
        cuda_cli: str | Path | None = None,
        environment: dict[str, str] | None = None,
        before_accept: Callable[[Path, dict[str, Any]], None] | None = None,
        terminal_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
        writable_runner: Callable[[Path, dict[str, Any]], dict[str, Any]] | None = None,
        cuda_discovery_runner: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> None:
        skills_root = Path(__file__).resolve().parents[2]
        self.todo_cli = Path(todo_cli or skills_root / "todo-orchestrator/scripts/todo.py")
        self.ctxpp_cli = Path(ctxpp_cli or skills_root / "cpp-context-compiler/scripts/ctxpp")
        self.worker_cli = Path(worker_cli or skills_root / "local-coding-worker/scripts/local_worker.py")
        self.cuda_cli = Path(cuda_cli or skills_root / "cuda/scripts/cuda_controller.py")
        self.environment = dict(environment or {})
        self.before_accept = before_accept
        self.terminal_runner = terminal_runner
        self.writable_runner = writable_runner
        self.cuda_discovery_runner = cuda_discovery_runner

    def _run_json(self, argv: list[str], *, cwd: Path, environment: dict[str, str] | None = None) -> dict[str, Any]:
        env = dict(os.environ)
        env.update(self.environment)
        env.update(environment or {})
        process = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)
        if process.returncode != 0:
            detail = (process.stdout.strip() or process.stderr.strip())[-1000:]
            raise IntegrationError(
                f"public integration command failed with exit code {process.returncode}: {detail}"
            )
        try:
            value = json.loads(process.stdout)
        except json.JSONDecodeError as error:
            raise IntegrationError("public integration command did not return JSON") from error
        if isinstance(value, dict) and value.get("ok") is True and isinstance(value.get("data"), dict):
            return dict(value["data"])
        if not isinstance(value, dict):
            raise IntegrationError("public integration command JSON must be an object")
        return value

    def _todo(self, root: Path, *arguments: str) -> dict[str, Any]:
        return self._run_json([sys.executable, str(self.todo_cli), *arguments, "--repo-root", str(root), "--json"], cwd=root)

    def _create_child(self, request: dict[str, Any]) -> dict[str, Any]:
        root = Path(request["repo_root"])
        argv = [
            "child", "create", "--claim-token", request["parent_claim_token"],
            "--objective", request["objective"],
            "--access", "read" if request["mode"] == "readonly" else "write",
        ]
        for scope in request["scopes"]:
            argv.extend(["--scope", scope])
        for gate in request["gates"]:
            argv.extend(["--gate", gate])
        child = self._todo(root, *argv)
        if child.get("task_id") != request["task_id"]:
            child_id = child.get("child_execution_id")
            if isinstance(child_id, str):
                self._todo(root, "child", "cancel", child_id, "--claim-token", request["parent_claim_token"])
            raise IntegrationError("todo child identity does not match the requested parent task")
        if not isinstance(child.get("child_token"), str) or not str(child["child_token"]).startswith("toch_"):
            raise IntegrationError("todo did not return a restricted child token")
        return child

    def request_from_claim(
        self, repo_root: str | Path, claim_token: str, *, mode: str, target: str | None = None,
    ) -> dict[str, Any]:
        root = Path(repo_root).resolve()
        capsule = self._todo(root, "context", "--claim-token", claim_token)
        task = _object(capsule.get("task"), "todo task capsule")
        scope = _object(capsule.get("scope"), "todo scope capsule")
        if mode == "auto":
            # Auto is deliberately conservative: bounded local assistance defaults
            # to read-only; edits require an explicit writable request.
            mode = "readonly"
        if mode not in {"readonly", "writable"}:
            raise IntegrationError("delegation mode must be auto, readonly, or writable")
        scopes = list(scope.get("exclusive_paths", []))
        if mode == "readonly":
            scopes.extend(scope.get("read_paths", []))
        scopes = sorted({str(item) for item in scopes if (root / str(item)).exists()})
        if not scopes:
            raise IntegrationError(f"todo task has no usable {mode} scope")
        gates = [str(item["id"]) for item in capsule.get("gates", [])
                 if isinstance(item, dict) and item.get("required") and item.get("id")]
        request: dict[str, Any] = {
            "format": "CORE4-INTEGRATION-REQUEST/2", "schema_version": 2,
            "mode": mode, "repo_root": str(root), "parent_claim_token": claim_token,
            "task_id": str(task["id"]), "objective": str(task["objective"]),
            "scopes": scopes, "gates": gates, "execution": {
                "backend": "real", "harness": "qwen", "gpu_count": 2,
            },
        }
        if mode == "readonly":
            request.update(role="review", target=target or "", intent="understand", budget_tokens=4096, max_items=12)
        else:
            if target:
                request["target"] = target
            gate_commands = []
            for gate_id in gates:
                explained = self._todo(root, "gate", "explain", gate_id)
                config = explained.get("config") if isinstance(explained.get("config"), dict) else {}
                argv = config.get("argv")
                if explained.get("type") in {"command", "benchmark", "json_predicate"} and isinstance(argv, list) and argv:
                    gate_commands.append({
                        "schema_version": 1, "argv": [str(item) for item in argv],
                        "cwd": str(config.get("cwd", ".")),
                        "env": {str(key): str(value) for key, value in dict(config.get("env") or {}).items()},
                        "timeout_seconds": float(config.get("timeout", 3600)),
                    })
            diff_check = {"schema_version": 1, "argv": ["git", "diff", "--check"],
                          "cwd": ".", "env": {}, "timeout_seconds": 60}
            request.update(
                baseline_commands=[diff_check], verification_commands=[*gate_commands, diff_check],
                acceptance_commands=[diff_check], read_dependencies=list(scope.get("read_paths", [])),
                approved_overlays=[],
            )
        return request

    def delegate(
        self, repo_root: str | Path, claim_token: str, *, mode: str, target: str | None = None,
    ) -> dict[str, Any]:
        return self.run(self.request_from_claim(repo_root, claim_token, mode=mode, target=target))

    def _writable_model(self, workspace: Path, request: dict[str, Any]) -> dict[str, Any]:
        import tomllib
        from .harnesses import QwenCodeAdapter
        from .result_validation import validate_model_outcome
        from .supervisor import SupervisorClient
        task_spec = json.dumps({
            "objective": request["objective"], "role": "edit",
            "read_paths": sorted(set([*request["scopes"], *request.get("read_dependencies", [])])),
            "write_paths": request["scopes"], "forbidden_paths": [], "target_symbols": [],
            "failing_tests": [], "interface_ids": [], "acceptance_gates": request["gates"],
        }, separators=(",", ":"))
        if request.get("target"):
            task_spec = json.dumps({
                **json.loads(task_spec), "target_symbols": [str(request["target"])],
            }, separators=(",", ":"))
        if not (workspace / ".ctxpp/index.jsonl").is_file():
            self._run_json([
                str(self.ctxpp_cli), "--root", str(workspace), "--json", "scan",
            ], cwd=workspace)
        packet = self._run_json([
            str(self.ctxpp_cli), "--root", str(workspace), "--json", "packet", "--task-spec", task_spec,
            "--consumer", "local-worker", "--budget", "1536", "--max-items", "4",
        ], cwd=workspace)
        supervisor = SupervisorClient(request["repo_root"])
        profile = tomllib.loads((Path(__file__).resolve().parents[1] /
                                 "config/production-profile.toml").read_text(encoding="utf-8"))
        execution = dict(request.get("execution") or {})
        admission_id = execution.get("admission_id")
        endpoint = supervisor.request("warm", **({"admission_id": admission_id} if admission_id else {}))
        harness = QwenCodeAdapter()
        handle = None
        task_runtime = tempfile.TemporaryDirectory(prefix="core4-qwen-task-")
        try:
            handle = harness.start({
                "cwd": str(workspace), "repository_root": str(workspace), "mode": "writable",
                "authorized_read_paths": sorted(set([*request["scopes"], *request.get("read_dependencies", [])])),
                "write_paths": request["scopes"], "allowed_tools": ["read_file", "edit", "structured_output"],
                **_qwen_budget_config(profile, writable=True),
                "base_url": endpoint["base_url"], "model": endpoint["model_id"],
                "runtime_dir": task_runtime.name,
            })
            model = harness.run(handle, {"prompt": json.dumps({
                "objective": request["objective"], "role": "implementation",
                "authorized_read_roots": sorted(set([*request["scopes"], *request.get("read_dependencies", [])])),
                "authorized_write_roots": request["scopes"], "packet": packet,
                "output_contract": "CORE4-MODEL-OUTCOME/1",
                "constraints": ("Call read_file once, call edit for the requested change, then call the tool named "
                                "structured_output as the final action. Do not finish with prose or printed JSON. "
                                "Every evidence and changed path must be repository-relative, never absolute. "
                                "Omit content_sha256 for an edited file unless computed after the final edit. "
                                "Edit only authorized roots. Do not run shell or agents. Escalate ambiguity."),
            }, separators=(",", ":"))})
            tracked = subprocess.run(
                ["git", "diff", "--name-only", "-z"], cwd=workspace, capture_output=True, check=True,
            ).stdout.split(b"\0")
            untracked = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=workspace,
                capture_output=True, check=True,
            ).stdout.split(b"\0")
            changed = sorted({item.decode("utf-8", errors="surrogateescape") for item in [*tracked, *untracked] if item})
            value = model.get("model_outcome")
            if not isinstance(value, dict):
                return {"status": "needs_codex", "summary": str(model.get("reason", "invalid model outcome"))[:500],
                        "model_outcome": None, "packet": packet, "usage": model.get("usage", {}),
                        "service": {key: endpoint.get(key) for key in
                                    ("slot_id", "service_lease_id", "server_pid", "gpu_uuids", "reused")},
                        "qwen_runtime_directory": task_runtime.name}
            validated = validate_model_outcome(
                value, repository_root=workspace,
                authorized_read_paths=sorted(set([*request["scopes"], *request.get("read_dependencies", [])])),
                write_paths=request["scopes"], actual_changed_paths=changed, mode="writable",
            )
            return {"status": validated["outcome"], "summary": validated["summary"],
                    "model_outcome": validated, "packet": packet, "usage": model.get("usage", {}),
                    "service": {key: endpoint.get(key) for key in
                                ("slot_id", "service_lease_id", "server_pid", "gpu_uuids", "reused")},
                    "qwen_runtime_directory": task_runtime.name}
        finally:
            if handle is not None:
                harness.evict(handle)
            try:
                supervisor.request("release", service_lease_id=endpoint.get("service_lease_id"))
            except Exception:
                pass
            task_runtime.cleanup()

    @staticmethod
    def _reverse_candidate(root: Path, artifact: dict[str, Any]) -> None:
        patch = Path(str(artifact["patch"]["path"])).read_bytes()
        checked = subprocess.run(["git", "apply", "--reverse", "--check", "--binary", "-"], cwd=root,
                                 input=patch, capture_output=True, check=False)
        if checked.returncode:
            raise IntegrationError("candidate rollback is unsafe")
        subprocess.run(["git", "apply", "--reverse", "--binary", "-"], cwd=root,
                       input=patch, capture_output=True, check=True)

    def _report(self, root: Path, child_token: str, status: str, summary: str,
                changed_paths: list[str] | None = None,
                references: dict[str, str] | None = None) -> dict[str, Any]:
        argv = [
            "child", "report", "--child-token", child_token,
            "--status", status, "--summary", summary[:500],
        ]
        for path in changed_paths or []:
            argv.extend(["--changed-path", path])
        for name, value in sorted((references or {}).items()):
            argv.extend([f"--{name.replace('_', '-')}-ref", value])
        return self._todo(root, *argv)

    @staticmethod
    def _candidate_root(root: Path, child_id: str) -> Path:
        process = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"], cwd=root, text=True,
            capture_output=True, check=False,
        )
        if process.returncode != 0:
            raise IntegrationError("cannot resolve Git common directory for candidate evidence")
        common = Path(process.stdout.strip())
        if not common.is_absolute():
            common = root / common
        destination = common.resolve() / "local-coding-worker/candidates" / child_id
        destination.mkdir(parents=True, exist_ok=True)
        return destination

    @staticmethod
    def _write_json(path: Path, value: object) -> str:
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        temporary = path.with_name(path.name + f".{uuid.uuid4().hex}.tmp")
        temporary.write_text(encoded, encoding="utf-8")
        os.replace(temporary, path)
        return str(path)

    def _status(self, request: dict[str, Any], child_id: str) -> dict[str, Any]:
        return self._todo(
            Path(request["repo_root"]), "child", "status", child_id,
            "--claim-token", request["parent_claim_token"],
        )

    def _terminal(self, worker_request: dict[str, Any]) -> dict[str, Any]:
        if self.terminal_runner is not None:
            return _object(self.terminal_runner(worker_request), "terminal worker result")
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(worker_request, handle)
            handle.flush()
            return self._run_json(
                [sys.executable, str(self.worker_cli), "run", "--request", handle.name],
                cwd=Path(worker_request["repo_root"]),
                environment={"LCW_TODO_CLI": str(self.todo_cli), "LCW_CTXPP_CLI": str(self.ctxpp_cli)},
            )

    def _cuda_discovery(self, request: dict[str, Any], acceptance: dict[str, Any] | None) -> dict[str, Any]:
        registry = request.get("cuda_registry")
        if not registry or not acceptance or acceptance.get("accepted") is not True:
            return {"state": "silent", "campaign_ids": []}
        packets = []
        for changed in acceptance.get("changed_paths", []):
            if Path(str(changed)).suffix.lower() not in {".c", ".cc", ".cpp", ".cxx", ".cu", ".cuh", ".h", ".hpp"}:
                continue
            try:
                packets.append(self._run_json(
                    [str(self.ctxpp_cli), "--root", request["repo_root"], "--json", "packet", str(changed),
                     "--consumer", "cuda", "--intent", "performance", "--budget", "1024", "--max-items", "8"],
                    cwd=Path(request["repo_root"]),
                ))
            except IntegrationError:
                pass
        evidence = {
            "schema_version": 1,
            "accepted_patches": [{"accepted": True, "changed_paths": acceptance["changed_paths"]}],
            "task_ids": [request["task_id"]],
            "context_packets": packets,
        }
        if self.cuda_discovery_runner is not None:
            result = _object(self.cuda_discovery_runner(evidence), "CUDA discovery result")
        else:
            with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
                json.dump(evidence, handle)
                handle.flush()
                result = self._run_json(
                    [sys.executable, str(self.cuda_cli), "registry", "discover", "--registry", str(registry),
                     "--input", handle.name, "--auto-queue", "--json"],
                    cwd=Path(request["repo_root"]),
                )
        matches = result.get("matches") if isinstance(result.get("matches"), list) else []
        campaign_ids = [str(item["campaign_id"]) for item in matches if isinstance(item, dict) and item.get("campaign_id")]
        status = str(result.get("status", "no_match"))
        auto_queue = result.get("auto_queue") if isinstance(result.get("auto_queue"), dict) else {}
        if status == "no_match":
            return {"state": "silent", "campaign_ids": [], "context_packets": len(packets)}
        if status == "ambiguous":
            return {
                "state": "choice_required", "campaign_ids": campaign_ids,
                "choices": [{"campaign_id": str(item["campaign_id"]), "reasons": len(item.get("reasons", []))}
                            for item in matches if isinstance(item, dict) and item.get("campaign_id")],
                "context_packets": len(packets), "auto_queued": False,
            }
        return {
            "state": "queued" if auto_queue.get("state") == "queued" else "selected",
            "status": status,
            "campaign_ids": campaign_ids,
            "context_packets": len(packets),
            "auto_queued": auto_queue.get("state") == "queued",
        }

    def _readonly(self, request: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
        execution = dict(request.get("execution") or {})
        version = 2 if execution else 1
        worker = {
            "format": f"LCW-REQUEST/{version}",
            "schema_version": version,
            "backend": str(execution.get("backend", "fake")),
            "role": request["role"],
            "readonly": True,
            "repo_root": request["repo_root"],
            "child_token": child["child_token"],
            "objective": request["objective"],
            "scopes": request["scopes"],
            "target": request["target"],
            "intent": request["intent"],
            "budget_tokens": request["budget_tokens"],
            "max_items": request["max_items"],
        }
        if execution:
            worker["execution"] = execution
        terminal = self._terminal(worker)
        status = str(terminal.get("status", "needs_codex"))
        if status not in {"completed", "no_change", "needs_codex", "failed", "preempted"}:
            raise IntegrationError(f"terminal read-only worker returned unsupported status: {status}")
        if terminal.get("child_reported") is not True:
            self._report(
                Path(request["repo_root"]), str(child["child_token"]),
                "needs_codex" if status in {"needs_codex", "preempted"} else "failed" if status == "failed" else "succeeded",
                str(terminal.get("summary", status)),
            )
        return {
            "status": status,
            "summary": str(terminal.get("summary", status))[:500],
            "changed_paths": [],
            "packet_hash": terminal.get("packet_hash"),
            "artifacts": list(terminal.get("artifacts", [])) if isinstance(terminal.get("artifacts"), list) else [],
            "model_outcome": terminal.get("model_outcome"),
            "accepted": False,
            "cuda": {"state": "silent", "campaign_ids": []},
        }

    def _writable(self, request: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
        root = Path(request["repo_root"])
        identity = _runtime_source()(root)
        scopes = normalize_scopes(request["scopes"])
        relevant_scopes = sorted(set([*scopes, *request.get("read_dependencies", [])]))
        relevant_before = _scope_state(root, relevant_scopes)
        changes = _object(request.get("fake_changes", {}), "fake_changes")
        normalized_changes = {_relative(path): content for path, content in changes.items()}
        if any(not isinstance(content, str) for content in normalized_changes.values()):
            raise IntegrationError("fake_changes values must be UTF-8 text strings")
        denied = [path for path in normalized_changes if not any(_inside(path, scope) for scope in scopes)]
        if denied:
            raise IntegrationError(f"fake changes exceed child scopes: {sorted(denied)}")
        artifact_root = self._candidate_root(root, str(child["child_execution_id"]))
        with materialize_writable_workspace(
                root, identity, scopes, request["baseline_commands"],
                read_dependencies=request.get("read_dependencies", []),
                approved_overlays=request.get("approved_overlays")) as workspace:
            reviewer = {}
            if self.writable_runner is not None:
                reviewer = _object(self.writable_runner(workspace.path, request), "writable runner result")
            elif request.get("execution", {}).get("backend") == "real":
                reviewer = self._writable_model(workspace.path, request)
                if reviewer.get("status") != "completed":
                    status = "needs_codex" if reviewer.get("status") == "needs_codex" else "failed"
                    self._report(root, str(child["child_token"]), status, str(reviewer.get("summary", status)))
                    return {
                        "status": status, "summary": str(reviewer.get("summary", status))[:500],
                        "changed_paths": [], "accepted": False, "artifact_root": str(artifact_root),
                        "cuda": {"state": "silent", "campaign_ids": []},
                    }
            else:
                for relative, content in sorted(normalized_changes.items()):
                    destination = workspace.path / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(content, encoding="utf-8")
            external = require_verification(workspace.path, request["verification_commands"], phase="external")
            artifact = build_patch_artifact(workspace, artifact_root, external)
        source_path = Path(artifact_root) / "source-identity.json"
        external_path = Path(artifact_root) / "candidate-verification.json"
        reviewer_path = Path(artifact_root) / "reviewer-evidence.json"
        acceptance_path = Path(artifact_root) / "acceptance-verification.json"
        self._write_json(source_path, identity)
        self._write_json(external_path, external)
        references = {
            "source_identity": str(source_path),
            "patch": str(artifact["patch"]["path"]),
            "candidate_verification": str(external_path),
            "acceptance_verification": str(acceptance_path),
        }
        if reviewer:
            self._write_json(reviewer_path, reviewer)
            references["reviewer_evidence"] = str(reviewer_path)
        if self.before_accept is not None:
            self.before_accept(root, artifact)
        try:
            def record(result: dict[str, Any]) -> bool:
                self._write_json(acceptance_path, result)
                return True
            with _ControllerAcceptanceLock(root):
                if _scope_state(root, relevant_scopes) != relevant_before:
                    raise StaleSourceError("task-relevant source changed after worker materialization")
                artifact["baseline_source_identity"] = _runtime_source()(root)
                acceptance = accept_patch_artifact(
                    root, artifact, request["acceptance_commands"], result_recorder=record,
                )
        except StaleSourceError:
            self._todo(root, "child", "stale", str(child["child_execution_id"]),
                       "--claim-token", request["parent_claim_token"])
            return {
                "status": "stale_patch", "summary": "Primary source changed before guarded acceptance.",
                "changed_paths": [], "accepted": False, "artifact_root": str(artifact_root),
                "cuda": {"state": "silent", "campaign_ids": []},
            }
        except AcceptanceError as error:
            self._report(root, str(child["child_token"]), "ready_for_acceptance", str(error)[:500],
                         artifact["changed_paths"], references)
            self._todo(root, "child", "reject", str(child["child_execution_id"]),
                       "--claim-token", request["parent_claim_token"])
            return {
                "status": "acceptance_failed", "summary": str(error)[:500],
                "changed_paths": [], "accepted": False, "artifact_root": str(artifact_root),
                "cuda": {"state": "silent", "campaign_ids": []},
            }
        try:
            for gate_id in request["gates"]:
                self._todo(root, "gate", "run", gate_id, "--claim-token", str(child["child_token"]))
            self._report(
                root, str(child["child_token"]), "ready_for_acceptance",
                "Externally verified writable candidate is ready for guarded acceptance.",
                artifact["changed_paths"], references,
            )
            for gate_id in request["gates"]:
                self._todo(
                    root, "gate", "run", gate_id, "--claim-token", request["parent_claim_token"],
                    "--accept-child", str(child["child_execution_id"]),
                )
            self._todo(root, "child", "accept", str(child["child_execution_id"]),
                       "--claim-token", request["parent_claim_token"])
        except Exception as error:
            self._reverse_candidate(root, artifact)
            try:
                state = self._status(request, str(child["child_execution_id"])).get("state")
                if state == "running":
                    self._report(root, str(child["child_token"]), "ready_for_acceptance", str(error)[:500],
                                 artifact["changed_paths"], references)
                self._todo(root, "child", "reject", str(child["child_execution_id"]),
                           "--claim-token", request["parent_claim_token"])
            except Exception:
                pass
            return {
                "status": "acceptance_failed", "summary": str(error)[:500], "changed_paths": [],
                "accepted": False, "artifact_root": str(artifact_root),
                "cuda": {"state": "silent", "campaign_ids": []},
            }
        return {
            "status": "accepted",
            "summary": "Externally verified patch accepted against current canonical source.",
            "changed_paths": list(acceptance["changed_paths"]),
            "accepted": True,
            "artifact_root": str(artifact_root),
            "cuda": self._cuda_discovery(request, acceptance),
        }

    def run(self, value: object) -> dict[str, Any]:
        request = normalize_integration_request(value)
        try:
            child = self._create_child(request)
        except Exception:
            execution = dict(request.get("execution") or {})
            admission_id = execution.get("admission_id")
            if admission_id:
                try:
                    from .supervisor import SupervisorClient
                    SupervisorClient(request["repo_root"]).request(
                        "cancel-admission", admission_id=admission_id,
                    )
                except Exception:
                    pass
            raise
        child_id = str(child["child_execution_id"])
        stop = threading.Event()
        heartbeat_errors: list[Exception] = []
        def heartbeat() -> None:
            while not stop.wait(60):
                try:
                    self._todo(Path(request["repo_root"]), "child", "heartbeat", "--child-token", str(child["child_token"]), "--lease-seconds", "300")
                except Exception as error:
                    heartbeat_errors.append(error)
                    return
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            outcome = self._readonly(request, child) if request["mode"] == "readonly" else self._writable(request, child)
        except Exception as error:
            try:
                self._report(Path(request["repo_root"]), str(child["child_token"]), "failed", str(error)[:500])
            except Exception:
                self._todo(
                    Path(request["repo_root"]), "child", "cancel", child_id,
                    "--claim-token", request["parent_claim_token"],
                )
            raise
        finally:
            stop.set()
            thread.join(timeout=2)
        if heartbeat_errors:
            raise IntegrationError(f"child heartbeat failed: {heartbeat_errors[0]}")
        status = self._status(request, child_id)
        return {
            "format": "CORE4-INTEGRATED-RESULT/1",
            "schema_version": 1,
            "task_id": request["task_id"],
            "child_execution_id": child_id,
            "child_state": status.get("state"),
            **outcome,
            "parent_task_completed": False,
        }


def normalize_integration_request(value: object) -> dict[str, Any]:
    request = _object(value, "integration request")
    version = request.get("schema_version")
    common = {
        "format", "schema_version", "mode", "repo_root", "parent_claim_token", "task_id",
        "objective", "scopes", "gates", "cuda_registry",
    }
    readonly = {"role", "target", "intent", "budget_tokens", "max_items"} | ({"execution"} if version == 2 else set())
    writable = {"fake_changes", "baseline_commands", "verification_commands", "acceptance_commands"}
    if version == 2:
        writable |= {"read_dependencies", "approved_overlays", "execution", "target"}
    if version not in {1, 2} or request.get("format") != f"CORE4-INTEGRATION-REQUEST/{version}":
        raise IntegrationError("integration request must use matching CORE4-INTEGRATION-REQUEST/1 or /2")
    mode = request.get("mode")
    if mode not in {"readonly", "writable"}:
        raise IntegrationError("integration mode must be readonly or writable")
    allowed = common | (readonly if mode == "readonly" else writable)
    unknown = sorted(set(request) - allowed)
    optional = {"cuda_registry"}
    if mode == "writable" and version == 2:
        optional |= {"fake_changes", "read_dependencies", "approved_overlays", "execution", "target"}
    missing = sorted((allowed - optional) - set(request))
    if unknown or missing:
        raise IntegrationError(f"integration request fields invalid: missing={missing} extra={unknown}")
    root = Path(str(request["repo_root"])).resolve()
    if not root.is_dir():
        raise IntegrationError("repo_root must exist")
    for name in ("parent_claim_token", "task_id", "objective"):
        if not isinstance(request[name], str) or not request[name]:
            raise IntegrationError(f"{name} must be a non-empty string")
    if not request["parent_claim_token"].startswith("toc_"):
        raise IntegrationError("parent_claim_token must be a todo parent claim token")
    scopes = normalize_scopes(request["scopes"])
    gates = request["gates"]
    if not isinstance(gates, list) or any(not isinstance(item, str) or not item for item in gates):
        raise IntegrationError("gates must be a list of non-empty strings")
    result = dict(request)
    result["repo_root"] = str(root)
    result["scopes"] = scopes
    result["gates"] = sorted(set(gates))
    if mode == "readonly":
        if request["role"] not in {"explain", "debug", "review", "test_plan"}:
            raise IntegrationError("unsupported read-only role")
        if request["intent"] not in {"understand", "debug", "test", "api", "performance"}:
            raise IntegrationError("unsupported ctxpp intent")
        if not isinstance(request["target"], str):
            raise IntegrationError("target must be a string")
        if not isinstance(request["budget_tokens"], int) or not 256 <= request["budget_tokens"] <= 12000:
            raise IntegrationError("budget_tokens must be between 256 and 12000")
        if not isinstance(request["max_items"], int) or not 1 <= request["max_items"] <= 32:
            raise IntegrationError("max_items must be between 1 and 32")
        if version == 2:
            execution = _object(request["execution"], "execution")
            if set(execution) - {"backend", "harness", "gpu_count", "service_profile", "harness_config", "admission_id"}:
                raise IntegrationError("execution contains unknown fields")
            if execution.get("backend") not in {"fake", "real"}:
                raise IntegrationError("execution backend must be fake or real")
    else:
        _object(request.get("fake_changes", {}), "fake_changes")
        for name in ("baseline_commands", "verification_commands", "acceptance_commands"):
            if not isinstance(request[name], list) or not request[name]:
                raise IntegrationError(f"{name} must be a non-empty command list")
        if version == 2:
            if "target" in request and (not isinstance(request["target"], str) or not request["target"]):
                raise IntegrationError("writable target must be a non-empty string")
            for name in ("read_dependencies", "approved_overlays"):
                values = request.get(name, [])
                if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
                    raise IntegrationError(f"{name} must be a list of non-empty strings")
            if "execution" in request:
                execution = _object(request["execution"], "execution")
                if set(execution) - {"backend", "harness", "gpu_count", "service_profile", "harness_config", "admission_id"}:
                    raise IntegrationError("execution contains unknown fields")
    registry = request.get("cuda_registry")
    if registry is not None:
        registry_path = Path(str(registry))
        if not registry_path.is_absolute():
            registry_path = root / registry_path
        result["cuda_registry"] = str(registry_path.resolve())
    return result
