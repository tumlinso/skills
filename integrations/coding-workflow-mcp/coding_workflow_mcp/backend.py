"""Composition over supported public skill CLIs using fixed argv arrays."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Sequence

from .handles import CapabilityStore, InvalidHandle
from .normalize import bounded_json, bounded_text, redact


EXPECTED_ENTRY_POINTS = {
    "todo": Path("todo-orchestrator/scripts/todo.py"),
    "ctxpp": Path("cpp-context-compiler/scripts/ctxpp"),
    "worker": Path("local-coding-worker/scripts/local_worker.py"),
    "cuda": Path("cuda/scripts/cuda_controller.py"),
}


class BackendError(RuntimeError):
    def __init__(self, code: str, diagnostic_id: str | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.diagnostic_id = diagnostic_id


def resolve_skills_root() -> Path:
    configured = os.environ.get("CODING_WORKFLOW_SKILLS_ROOT")
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured).expanduser())
    here = Path(__file__).resolve()
    candidates.extend(parent for parent in here.parents if parent.name == "integrations")
    for candidate in candidates:
        root = candidate.parent if candidate.name == "integrations" else candidate
        resolved = root.resolve()
        if all((resolved / relative).is_file() for relative in EXPECTED_ENTRY_POINTS.values()):
            return resolved
    missing = ", ".join(str(path) for path in EXPECTED_ENTRY_POINTS.values())
    raise BackendError(f"skills_root_missing_expected_entry_points:{missing}")


class CodingWorkflowBackend:
    """Thin adapter; semantic decisions remain in the four underlying skills."""

    def __init__(self, store: CapabilityStore | None = None, skills_root: Path | None = None) -> None:
        self.store = store or CapabilityStore()
        self.skills_root = (skills_root or resolve_skills_root()).resolve()
        self.entry_points = {name: self.skills_root / path for name, path in EXPECTED_ENTRY_POINTS.items()}

    def _diagnostic(self, stderr: str) -> str:
        clean = str(redact(bounded_text(stderr, 16_384)))
        return self.store.write_diagnostic(clean)

    def _run_json(
        self,
        argv: Sequence[str],
        *,
        cwd: Path,
        timeout: float = 30,
        allow_failure: bool = False,
    ) -> dict[str, Any]:
        if isinstance(argv, (str, bytes)):
            raise TypeError("subprocess argv must be a sequence, not a shell string")
        result = subprocess.run(
            [str(item) for item in argv],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
            env=os.environ.copy(),
        )
        try:
            value = json.loads(result.stdout)
        except json.JSONDecodeError:
            diagnostic_id = self._diagnostic(result.stderr + "\n" + result.stdout)
            raise BackendError("invalid_public_cli_envelope", diagnostic_id) from None
        if result.returncode and not allow_failure:
            diagnostic_id = self._diagnostic(result.stderr)
            raise BackendError("public_cli_failed", diagnostic_id)
        if not isinstance(value, dict):
            raise BackendError("invalid_public_cli_envelope")
        return value

    def canonical_repo(self, repo_root: str) -> Path:
        candidate = Path(repo_root).expanduser()
        if not candidate.is_absolute():
            candidate = Path.cwd() / candidate
        result = subprocess.run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
            check=False,
            shell=False,
        )
        if result.returncode:
            raise BackendError("repo_root_is_not_a_git_repository", self._diagnostic(result.stderr))
        return Path(result.stdout.strip()).resolve()

    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["todo"]), *arguments, "--repo-root", str(repo), "--json"],
            cwd=repo,
            allow_failure=allow_failure,
        )

    def ctxpp(self, repo: Path, *arguments: str) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["ctxpp"]), "--root", str(repo), "--json", *arguments],
            cwd=repo,
            allow_failure=True,
        )

    def worker(self, repo: Path, *arguments: str, timeout: float = 30) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["worker"]), *arguments, "--json"],
            cwd=repo,
            timeout=timeout,
            allow_failure=True,
        )

    def cuda(self, repo: Path, *arguments: str) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["cuda"]), *arguments, "--json"],
            cwd=repo,
            allow_failure=True,
        )

    @staticmethod
    def _data(envelope: dict[str, Any]) -> dict[str, Any]:
        data = envelope.get("data")
        return dict(data) if isinstance(data, dict) else envelope

    @staticmethod
    def _compact_task_capsule(data: dict[str, Any], workflow_handle: str) -> dict[str, Any]:
        task = data.get("task") if isinstance(data.get("task"), dict) else {}
        scope = data.get("scope") if isinstance(data.get("scope"), dict) else {}
        interlocks = data.get("interlocks") if isinstance(data.get("interlocks"), list) else []
        gates = data.get("gates") if isinstance(data.get("gates"), list) else []
        result = {
            "status": "claimed",
            "workflow_handle": workflow_handle,
            "revision": data.get("project_revision"),
            "task": {
                "id": task.get("id"),
                "title": task.get("title", ""),
                "objective": task.get("objective", ""),
                "next_action": task.get("next_action", ""),
            },
            "scope": {
                "write": list(scope.get("exclusive_paths", []))[:32],
                "read": list(scope.get("read_paths", []))[:32],
                "forbidden": list(scope.get("forbidden_paths", []))[:32],
            },
            "constraints": [
                str(item.get("rule"))[:500]
                for item in interlocks[:12]
                if isinstance(item, dict) and item.get("rule")
            ],
            "gates": [
                {"id": item.get("id"), "type": item.get("type"), "required": bool(item.get("required"))}
                for item in gates[:24]
                if isinstance(item, dict) and item.get("id")
            ],
            "local_delegation": {
                "recommended_mode": "none",
                "reason": "optional; delegate_task auto defers eligibility and admission to local-worker",
            },
        }
        return bounded_json(result, 4_000)

    def next_task(self, repo_root: str, task_id: str | None = None) -> dict[str, Any]:
        repo = self.canonical_repo(repo_root)
        bootstrap = self._data(self.todo(repo, "bootstrap", allow_failure=True))
        arguments = ["continue"]
        if task_id:
            arguments.extend(["--task-id", task_id])
        continued = self.todo(repo, *arguments, allow_failure=True)
        data = self._data(continued)
        claim = data.get("claim") if isinstance(data.get("claim"), dict) else {}
        session = data.get("session") if isinstance(data.get("session"), dict) else {}
        task = data.get("task") if isinstance(data.get("task"), dict) else {}
        claim_token = claim.get("claim_token")
        session_token = session.get("session_token")
        if not all(isinstance(value, str) and value for value in (claim_token, session_token, task.get("id"))):
            status = str(data.get("status") or data.get("code") or continued.get("code") or "idle")
            if status not in {"idle", "blocked", "attention_required"}:
                status = "blocked" if "block" in status else "idle"
            reason = data.get("reason") or data.get("message") or "no task is currently claimable"
            return bounded_json({"status": status, "reason": str(reason)[:700]}, 4_000)
        record = {
            "repo": str(repo),
            "project_uuid": bootstrap.get("project_uuid") or data.get("project_uuid"),
            "session_token": session_token,
            "claim_token": claim_token,
            "task_id": str(task["id"]),
            "revision": data.get("project_revision"),
        }
        handle = self.store.create_workflow(record)
        return self._compact_task_capsule(data, handle)

    def _active_workflow(self, workflow_handle: str) -> tuple[dict[str, Any], Path, dict[str, Any]]:
        record = self.store.get_workflow(workflow_handle)
        repo = Path(record["repo"])
        pulse = self.todo(
            repo, "pulse", "--claim-token", str(record["claim_token"]), allow_failure=True
        )
        data = self._data(pulse)
        if pulse.get("ok") is False or data.get("code") in {"invalid_claim", "stale_claim", "not_found"}:
            raise InvalidHandle("workflow capability is no longer active")
        if data.get("project_revision") is not None:
            record["revision"] = data["project_revision"]
            self.store.update(workflow_handle, record)
        return record, repo, data

    def inspect_task(
        self,
        workflow_handle: str,
        focus: str,
        target: str | None,
        intent: str,
        budget_tokens: int,
    ) -> dict[str, Any]:
        record, repo, pulse = self._active_workflow(workflow_handle)
        if focus == "task":
            context = self._data(self.todo(repo, "context", "--claim-token", record["claim_token"], allow_failure=True))
            task = context.get("task") if isinstance(context.get("task"), dict) else {}
            scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
            return bounded_json({
                "status": "current",
                "revision": context.get("project_revision", pulse.get("project_revision")),
                "task": {key: task.get(key) for key in ("id", "title", "objective", "next_action")},
                "scope": {
                    "write": list(scope.get("exclusive_paths", []))[:32],
                    "read": list(scope.get("read_paths", []))[:32],
                    "forbidden": list(scope.get("forbidden_paths", []))[:32],
                },
                "gates": [
                    {key: item.get(key) for key in ("id", "type", "required", "status")}
                    for item in list(context.get("gates", []))[:24] if isinstance(item, dict)
                ],
            }, 6_000)
        if focus == "source":
            arguments = ["packet", "--consumer", "coding-workflow", "--intent", intent,
                         "--budget", str(budget_tokens), "--max-items", "12"]
            if target:
                arguments.append(target)
            try:
                packet = self._data(self.ctxpp(repo, *arguments))
            except BackendError:
                return {"status": "unavailable", "fallback": "use_normal_repository_tools"}
            if packet.get("ok") is False or packet.get("error"):
                return {"status": "unavailable", "fallback": "use_normal_repository_tools"}
            compact = {
                "status": "available",
                "target": packet.get("target"),
                "route": packet.get("route") or packet.get("canonical_targets"),
                "edit_locations": packet.get("edit_locations") or packet.get("locations"),
                "trust": packet.get("trust"),
                "interfaces": packet.get("interfaces"),
                "tests": packet.get("tests") or packet.get("relevant_tests"),
                "content": packet.get("content") or packet.get("canonical_content") or packet.get("items"),
            }
            return bounded_json({key: value for key, value in compact.items() if value not in (None, [], {})}, 6_000)
        history = self._data(self.todo(
            repo, "context", "--claim-token", record["claim_token"], "--section", "history", allow_failure=True
        ))
        evidence = history.get("history") or history.get("events") or history.get("evidence") or []
        return bounded_json({"status": "available", "evidence": list(evidence)[-20:]}, 6_000)

    def delegate_task(self, workflow_handle: str, mode: str, target: str | None) -> dict[str, Any]:
        record, repo, _ = self._active_workflow(workflow_handle)
        arguments = ["delegate", "--claim-token", record["claim_token"], "--mode", mode]
        if target:
            arguments.extend(["--target", target])
        response = self._data(self.worker(repo, *arguments))
        status = response.get("status")
        if status == "local_unavailable":
            if response.get("child_created") is not False or response.get("scope_locked") is not False:
                return {
                    "status": "attention_required",
                    "reason": "local_worker_admission_contract_missing_no_child_no_scope_guarantee",
                    "fallback": "continue_frontier",
                }
            return bounded_json({
                "status": "local_unavailable",
                "reason": response.get("reason", "all_local_worker_slots_busy"),
                "fallback": "continue_frontier",
                "retry_recommended": False,
                "child_created": False,
                "scope_locked": False,
            }, 700)
        if status == "not_eligible":
            return bounded_json({
                "status": "not_eligible",
                "reason": response.get("reason", "task_is_not_bounded_for_local_execution"),
                "fallback": "continue_frontier",
            }, 700)
        execution_id = response.get("execution_id")
        delegated_mode = response.get("mode") or (mode if mode != "auto" else response.get("admitted_mode"))
        if status != "delegated" or not isinstance(execution_id, str) or delegated_mode not in {"readonly", "writable"}:
            return {
                "status": "attention_required",
                "reason": "local_worker_public_admission_delegate_contract_unavailable",
                "fallback": "continue_frontier",
            }
        alias = self.store.create_delegation({
            "repo": str(repo), "execution_id": execution_id,
            "workflow_handle": workflow_handle, "mode": delegated_mode,
        })
        return {"status": "delegated", "delegation_handle": alias, "mode": delegated_mode}

    def collect_delegation(self, delegation_handle: str) -> dict[str, Any]:
        record = self.store.get_delegation(delegation_handle)
        repo = Path(record["repo"])
        response = self._data(self.worker(repo, "delegate", "--collect", record["execution_id"]))
        status = response.get("status") or response.get("state")
        if status == "running":
            return {"status": "running", "instruction": "continue_frontier_or_collect_later", "poll_recommended": False}
        result = response.get("result") if isinstance(response.get("result"), dict) else response
        status = result.get("status") or status
        if status == "succeeded":
            status = "completed"
        allowed = {"completed", "accepted", "needs_codex", "failed", "preempted", "stale", "local_unavailable"}
        if status not in allowed:
            status = "failed"
        terminal = {
            "status": status,
            "summary": str(result.get("summary") or result.get("reason") or "")[:1000],
            "changed_paths": list(result.get("changed_paths") or [])[:32],
            "verification": list(result.get("verification") or [])[:24],
            "risk": result.get("risk", "unknown"),
            "blocker": result.get("blocker"),
            "parent_task_completed": False,
        }
        record["status"] = status
        self.store.update(delegation_handle, record, terminal=True)
        return bounded_json(terminal, 4_000)

    def finish_task(
        self,
        workflow_handle: str,
        action: str,
        disposition: str,
        note: str | None,
        reason: str | None,
    ) -> dict[str, Any]:
        record, repo, _ = self._active_workflow(workflow_handle)
        if action == "block" and not reason:
            return {"status": "invalid_request", "reason": "reason_is_required_for_block"}
        arguments = [action, "--claim-token", record["claim_token"]]
        if action == "complete":
            arguments.extend(["--disposition", disposition])
        elif action == "release":
            arguments.extend(["--status", disposition])
        if note and action != "release":
            arguments.extend(["--note", note[:1000]])
        if reason and action in {"block", "handoff", "release"}:
            arguments.extend(["--reason", reason[:1000]])
        envelope = self.todo(repo, *arguments, allow_failure=True)
        data = self._data(envelope)
        if envelope.get("ok") is False:
            missing = data.get("missing_gate_ids") or data.get("missing_gates") or []
            if missing or "gate" in str(envelope.get("code", "")):
                return {"status": "gate_required", "missing_gate_ids": list(missing)[:24]}
            return {"status": "attention_required", "reason": str(envelope.get("code", "todo_disposition_failed"))[:300]}
        self.store.delete(workflow_handle)
        return bounded_json({
            "status": "finished", "action": action, "disposition": disposition,
            "task_id": record["task_id"], "revision": data.get("project_revision"),
        }, 2_000)
