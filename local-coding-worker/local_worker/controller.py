"""CORE4 integration controller over frozen public skill interfaces."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from .acceptance import AcceptanceError, StaleSourceError, accept_patch_artifact, build_patch_artifact
from .verification import require_verification
from .workspace import materialize_writable_workspace, normalize_scopes


class IntegrationError(RuntimeError):
    pass


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
    ) -> None:
        skills_root = Path(__file__).resolve().parents[2]
        self.todo_cli = Path(todo_cli or skills_root / "todo-orchestrator/scripts/todo.py")
        self.ctxpp_cli = Path(ctxpp_cli or skills_root / "cpp-context-compiler/scripts/ctxpp")
        self.worker_cli = Path(worker_cli or skills_root / "local-coding-worker/scripts/local_worker.py")
        self.cuda_cli = Path(cuda_cli or skills_root / "cuda/scripts/cuda_controller.py")
        self.environment = dict(environment or {})
        self.before_accept = before_accept
        self.terminal_runner = terminal_runner

    def _run_json(self, argv: list[str], *, cwd: Path, environment: dict[str, str] | None = None) -> dict[str, Any]:
        env = dict(os.environ)
        env.update(self.environment)
        env.update(environment or {})
        process = subprocess.run(argv, cwd=cwd, env=env, text=True, capture_output=True, check=False)
        if process.returncode != 0:
            raise IntegrationError(f"public integration command failed with exit code {process.returncode}")
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

    def _report(self, root: Path, child_token: str, status: str, summary: str,
                changed_paths: list[str] | None = None) -> dict[str, Any]:
        argv = [
            "child", "report", "--child-token", child_token,
            "--status", status, "--summary", summary[:500],
        ]
        for path in changed_paths or []:
            argv.extend(["--changed-path", path])
        return self._todo(root, *argv)

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
        evidence = {
            "schema_version": 1,
            "accepted_patches": [{"accepted": True, "changed_paths": acceptance["changed_paths"]}],
            "task_ids": [request["task_id"]],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8") as handle:
            json.dump(evidence, handle)
            handle.flush()
            result = self._run_json(
                [sys.executable, str(self.cuda_cli), "registry", "discover", "--registry", str(registry),
                 "--input", handle.name, "--json"],
                cwd=Path(request["repo_root"]),
            )
        matches = result.get("matches") if isinstance(result.get("matches"), list) else []
        campaign_ids = [str(item["campaign_id"]) for item in matches if isinstance(item, dict) and item.get("campaign_id")]
        return {
            "state": "triggered" if campaign_ids else "silent",
            "status": result.get("status"),
            "campaign_ids": campaign_ids,
            "auto_queued": False,
        }

    def _readonly(self, request: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
        worker = {
            "format": "LCW-REQUEST/1",
            "schema_version": 1,
            "backend": "fake",
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
        terminal = self._terminal(worker)
        status = str(terminal.get("status", "needs_codex"))
        if status not in {"no_change", "needs_codex"}:
            raise IntegrationError(f"terminal read-only worker returned unsupported status: {status}")
        if terminal.get("child_reported") is not True:
            self._report(
                Path(request["repo_root"]), str(child["child_token"]),
                "needs_codex" if status == "needs_codex" else "succeeded",
                str(terminal.get("summary", status)),
            )
        return {
            "status": status,
            "summary": str(terminal.get("summary", status))[:500],
            "changed_paths": [],
            "packet_hash": terminal.get("packet_hash"),
            "accepted": False,
            "cuda": {"state": "silent", "campaign_ids": []},
        }

    def _writable(self, request: dict[str, Any], child: dict[str, Any]) -> dict[str, Any]:
        root = Path(request["repo_root"])
        identity = _runtime_source()(root)
        scopes = normalize_scopes(request["scopes"])
        changes = _object(request["fake_changes"], "fake_changes")
        normalized_changes = {_relative(path): content for path, content in changes.items()}
        if any(not isinstance(content, str) for content in normalized_changes.values()):
            raise IntegrationError("fake_changes values must be UTF-8 text strings")
        denied = [path for path in normalized_changes if not any(_inside(path, scope) for scope in scopes)]
        if denied:
            raise IntegrationError(f"fake changes exceed child scopes: {sorted(denied)}")
        with tempfile.TemporaryDirectory(prefix="core4-patch-artifacts-") as artifact_root:
            with materialize_writable_workspace(root, identity, scopes, request["baseline_commands"]) as workspace:
                for relative, content in sorted(normalized_changes.items()):
                    destination = workspace.path / relative
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_text(content, encoding="utf-8")
                external = require_verification(workspace.path, request["verification_commands"], phase="external")
                artifact = build_patch_artifact(workspace, artifact_root, external)
            self._report(root, str(child["child_token"]), "succeeded", "Verified writable fake-backend patch.", artifact["changed_paths"])
            if self.before_accept is not None:
                self.before_accept(root, artifact)
            try:
                acceptance = accept_patch_artifact(root, artifact, request["acceptance_commands"])
            except StaleSourceError:
                return {
                    "status": "stale_patch", "summary": "Primary source changed before guarded acceptance.",
                    "changed_paths": [], "accepted": False,
                    "cuda": {"state": "silent", "campaign_ids": []},
                }
            except AcceptanceError as error:
                return {
                    "status": "acceptance_failed", "summary": str(error)[:500],
                    "changed_paths": [], "accepted": False,
                    "cuda": {"state": "silent", "campaign_ids": []},
                }
        return {
            "status": "accepted",
            "summary": "Externally verified patch accepted against current canonical source.",
            "changed_paths": list(acceptance["changed_paths"]),
            "accepted": True,
            "cuda": self._cuda_discovery(request, acceptance),
        }

    def run(self, value: object) -> dict[str, Any]:
        request = normalize_integration_request(value)
        child = self._create_child(request)
        child_id = str(child["child_execution_id"])
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
    common = {
        "format", "schema_version", "mode", "repo_root", "parent_claim_token", "task_id",
        "objective", "scopes", "gates", "cuda_registry",
    }
    readonly = {"role", "target", "intent", "budget_tokens", "max_items"}
    writable = {"fake_changes", "baseline_commands", "verification_commands", "acceptance_commands"}
    if request.get("format") != "CORE4-INTEGRATION-REQUEST/1" or request.get("schema_version") != 1:
        raise IntegrationError("integration request must use CORE4-INTEGRATION-REQUEST/1 schema_version 1")
    mode = request.get("mode")
    if mode not in {"readonly", "writable"}:
        raise IntegrationError("integration mode must be readonly or writable")
    allowed = common | (readonly if mode == "readonly" else writable)
    unknown = sorted(set(request) - allowed)
    missing = sorted((allowed - {"cuda_registry"}) - set(request))
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
        if not isinstance(request["target"], str) or not request["target"]:
            raise IntegrationError("target must be a non-empty string")
        if not isinstance(request["budget_tokens"], int) or not 256 <= request["budget_tokens"] <= 12000:
            raise IntegrationError("budget_tokens must be between 256 and 12000")
        if not isinstance(request["max_items"], int) or not 1 <= request["max_items"] <= 32:
            raise IntegrationError("max_items must be between 1 and 32")
    else:
        _object(request["fake_changes"], "fake_changes")
        for name in ("baseline_commands", "verification_commands", "acceptance_commands"):
            if not isinstance(request[name], list) or not request[name]:
                raise IntegrationError(f"{name} must be a non-empty command list")
    registry = request.get("cuda_registry")
    if registry is not None:
        registry_path = Path(str(registry))
        if not registry_path.is_absolute():
            registry_path = root / registry_path
        result["cuda_registry"] = str(registry_path.resolve())
    return result
