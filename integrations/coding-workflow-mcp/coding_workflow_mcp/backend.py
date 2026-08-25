"""Composition over supported public skill CLIs using fixed argv arrays."""

from __future__ import annotations

import json
import os
from pathlib import Path
import fcntl
import secrets
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
        self.instance_id = "fi_" + secrets.token_urlsafe(24)

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
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        if isinstance(argv, (str, bytes)):
            raise TypeError("subprocess argv must be a sequence, not a shell string")
        environment = os.environ.copy()
        environment.update(extra_env or {})
        result = subprocess.run(
            [str(item) for item in argv],
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
            shell=False,
            env=environment,
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

    def todo(
        self,
        repo: Path,
        *arguments: str,
        allow_failure: bool = False,
        extra_env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["todo"]), *arguments, "--repo-root", str(repo), "--json"],
            cwd=repo,
            allow_failure=allow_failure,
            extra_env=extra_env,
        )

    def ctxpp(self, repo: Path, *arguments: str, timeout: float = 30) -> dict[str, Any]:
        return self._run_json(
            [sys.executable, str(self.entry_points["ctxpp"]), "--root", str(repo), "--json", *arguments],
            cwd=repo,
            timeout=timeout,
            allow_failure=True,
        )

    @staticmethod
    def _ctxpp_lock(repo: Path):
        common_raw = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"], cwd=repo, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, shell=False,
        ).stdout.strip()
        common = Path(common_raw) if Path(common_raw).is_absolute() else repo / common_raw
        lock_root = common.resolve() / "local-coding-worker/locks"
        lock_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        return (lock_root / "ctxpp-preflight.lock").open("a+b")

    def _recover_inspection_packet(
        self, repo: Path, record: dict[str, Any], target: str | None,
        intent: str, budget_tokens: int,
    ) -> dict[str, Any] | None:
        if not target:
            return None
        candidate = Path(target)
        if candidate.is_absolute() or ".." in candidate.parts:
            return None
        source = repo / candidate
        if not source.is_file() or source.is_symlink() or source.suffix.lower() not in {
            ".c", ".cc", ".cpp", ".cxx", ".cu", ".cuh", ".h", ".hh", ".hpp", ".hxx",
        }:
            return None
        context = self._data(self.todo(
            repo, "context", "--claim-token", str(record["claim_token"]), allow_failure=True,
        ))
        scope = context.get("scope") if isinstance(context.get("scope"), dict) else {}
        authorized = [
            str(item).rstrip("/") for key in ("exclusive_paths", "read_paths")
            for item in scope.get(key, []) if isinstance(item, str) and item
        ]
        relative = candidate.as_posix()
        if not any(relative == root or relative.startswith(root + "/") for root in authorized):
            return None
        if not (repo / ".ctxpp.toml").is_file():
            return None
        stream = self._ctxpp_lock(repo)
        try:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            arguments = ["packet", "--consumer", "coding-workflow", "--intent", intent,
                         "--budget", str(budget_tokens), "--max-items", "12", target]
            try:
                return self._data(self.ctxpp(repo, *arguments))
            except BackendError:
                pass
            self.ctxpp(repo, "init", "--no-build-core", "--no-scan", timeout=60)
            self.ctxpp(repo, "scan", relative, timeout=300)
            return self._data(self.ctxpp(repo, *arguments))
        except (BackendError, OSError, subprocess.SubprocessError):
            return None
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
            stream.close()

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

    def next_task(
        self,
        repo_root: str,
        task_id: str | None = None,
        recovery_approval: str | None = None,
    ) -> dict[str, Any]:
        repo = self.canonical_repo(repo_root)
        bootstrap = self._data(self.todo(repo, "bootstrap", allow_failure=True))
        project_uuid = bootstrap.get("project_uuid")
        if recovery_approval is not None and (
            not isinstance(recovery_approval, str)
            or not recovery_approval.startswith("toa_")
            or not task_id
        ):
            return {"status": "override_requires_permission", "reason": "valid_manual_approval_required"}
        if task_id:
            recovered = self._recover_workflow(repo, task_id, project_uuid)
            if recovered is not None:
                return recovered
            inspected = self.todo(repo, "recover", "live-inspect", task_id, allow_failure=True)
            inspected_data = self._data(inspected)
            if inspected.get("ok") is not False and inspected_data.get("owner_system") == "coding-workflow":
                if not recovery_approval:
                    return bounded_json({
                        "status": "override_requires_permission",
                        "reason": "facade_capability_missing_for_live_claim",
                        "claim_fingerprint": inspected_data.get("claim_fingerprint"),
                        "revision": inspected_data.get("project_revision"),
                        "blockers": list(inspected_data.get("blockers") or [])[:12],
                        "safe_operation": "human_create_exact_live_claim_approval_out_of_band",
                    }, 1_200)
                return self._consume_live_override(
                    repo, task_id, recovery_approval, str(project_uuid or "")
                )
        arguments = ["continue"]
        if task_id:
            arguments.extend(["--task-id", task_id])
        arguments.extend([
            "--owner-system", "coding-workflow", "--owner-instance", self.instance_id,
        ])
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
            "claim_fingerprint": claim.get("claim_fingerprint"),
            "lineage_fingerprints": [claim.get("claim_fingerprint")]
            if claim.get("claim_fingerprint") else [],
        }
        handle = self.store.create_workflow(record)
        return self._compact_task_capsule(data, handle)

    def _consume_live_override(
        self,
        repo: Path,
        task_id: str,
        approval: str,
        project_uuid: str,
    ) -> dict[str, Any]:
        envelope = self.todo(
            repo,
            "recover",
            "live-override",
            task_id,
            "--new-owner-instance",
            self.instance_id,
            allow_failure=True,
            extra_env={"CODING_WORKFLOW_RECOVERY_APPROVAL": approval},
        )
        if envelope.get("ok") is False:
            code = str(envelope.get("code") or "override_failed")
            allowed = {
                "override_requires_permission", "approval_consumed", "stale_approval",
                "approval_mismatch", "live_override_blocked",
            }
            status = code if code in allowed else "attention_required"
            details = envelope.get("error", {}).get("details", {}) if isinstance(envelope.get("error"), dict) else {}
            blockers = details.get("blockers", []) if isinstance(details, dict) else []
            return bounded_json({
                "status": status,
                "reason": code,
                "blockers": list(blockers)[:12] if isinstance(blockers, list) else [],
            }, 1_200)
        data = self._data(envelope)
        claim = data.get("claim") if isinstance(data.get("claim"), dict) else {}
        session = data.get("session") if isinstance(data.get("session"), dict) else {}
        task = data.get("task") if isinstance(data.get("task"), dict) else {}
        values = (claim.get("claim_token"), session.get("session_token"), task.get("id"))
        if not all(isinstance(value, str) and value for value in values):
            return {"status": "attention_required", "reason": "invalid_live_override_envelope"}
        lineage = [
            value for value in (
                claim.get("retired_claim_fingerprint"), claim.get("claim_fingerprint")
            ) if isinstance(value, str) and value
        ]
        record = {
            "repo": str(repo), "project_uuid": project_uuid,
            "session_token": session["session_token"], "claim_token": claim["claim_token"],
            "task_id": str(task["id"]), "revision": data.get("project_revision"),
            "claim_fingerprint": claim.get("claim_fingerprint"),
            "lineage_fingerprints": lineage,
            "manual_override": True,
        }
        handle = self.store.create_workflow(record)
        result = self._compact_task_capsule(data, handle)
        result["manually_recovered"] = True
        return bounded_json(result, 4_000)

    def _recover_workflow(
        self,
        repo: Path,
        task_id: str,
        project_uuid: Any,
    ) -> dict[str, Any] | None:
        """Reissue a facade-owned active claim without asking todo to claim again."""
        expected_project = project_uuid if isinstance(project_uuid, str) and project_uuid else None
        # A terminal disposition can remove the candidate between validation
        # and reissue, so refresh the bounded candidate set once.
        for _ in range(2):
            candidates = self.store.find_workflows(repo, task_id, expected_project)
            if not candidates:
                return None
            for old_handle, record in candidates:
                pulse = self.todo(
                    repo,
                    "pulse",
                    "--claim-token",
                    str(record.get("claim_token", "")),
                    allow_failure=True,
                )
                pulse_data = self._data(pulse)
                if pulse.get("ok") is False:
                    code = str(pulse.get("code") or pulse_data.get("code") or "")
                    if code in {"invalid_claim", "stale_claim", "not_found", "claim_not_active"}:
                        self.store.delete(old_handle)
                        continue
                    return bounded_json({
                        "status": "attention_required",
                        "reason": "stored_claim_validation_unavailable",
                        "safe_operation": "retry_next_task",
                    }, 4_000)
                context_envelope = self.todo(
                    repo,
                    "context",
                    "--claim-token",
                    str(record.get("claim_token", "")),
                    allow_failure=True,
                )
                context = self._data(context_envelope)
                context_task = context.get("task") if isinstance(context.get("task"), dict) else {}
                if context_envelope.get("ok") is False or context_task.get("id") != task_id:
                    return bounded_json({
                        "status": "attention_required",
                        "reason": "stored_claim_context_unavailable",
                        "safe_operation": "retry_next_task",
                    }, 4_000)
                if pulse_data.get("project_revision") is not None:
                    record["revision"] = pulse_data["project_revision"]
                try:
                    replacement = self.store.reissue_workflow(old_handle, record)
                except InvalidHandle:
                    continue
                result = self._compact_task_capsule(context, replacement)
                result["resumed"] = True
                return bounded_json(result, 4_000)
        return bounded_json({
            "status": "attention_required",
            "reason": "workflow_recovery_raced",
            "safe_operation": "retry_next_task",
        }, 4_000)

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
                packet = self._recover_inspection_packet(repo, record, target, intent, budget_tokens)
                if packet is None:
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
            arguments.extend(["--objective", target])
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
            result = {
                "status": "not_eligible",
                "reason": response.get("reason", "task_is_not_bounded_for_local_execution"),
                "fallback": "continue_frontier",
            }
            for key in ("child_created", "scope_locked", "admission_created", "model_started"):
                if response.get(key) is False:
                    result[key] = False
            return bounded_json(result, 700)
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
        elif status == "no_change":
            status = "completed"
        allowed = {"completed", "accepted", "needs_codex", "failed", "preempted", "stale", "local_unavailable"}
        if status not in allowed:
            status = "failed"
        terminal = {
            "status": status,
            "summary": str(result.get("summary") or result.get("reason") or result.get("error") or "")[:1000],
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
        self.store.delete_workflow_family(record)
        return bounded_json({
            "status": "finished", "action": action, "disposition": disposition,
            "task_id": record["task_id"], "revision": data.get("project_revision"),
        }, 2_000)
