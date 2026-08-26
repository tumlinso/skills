"""Official-SDK stdio server construction without startup side effects."""

from __future__ import annotations

from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .backend import BackendError, CodingWorkflowBackend
from .handles import InvalidHandle


SERVER_INSTRUCTIONS = (
    "For substantial repository work, coding-workflow is the mandatory first front door. "
    "Do not pre-claim with todo-orchestrator or start implementation before next_task. "
    "After a claim, specialized skills are bounded helpers. Use lower-level CLIs only if this "
    "facade is unavailable, broken, or under debugging. Call next_task once and stay in scope. "
    "delegate_task is opportunistic: on local_unavailable or not_eligible, continue in Codex; "
    "never wait or poll. Collect only returned delegation handles and finish every claim with "
    "finish_task. Use inspect_task for bounded context. Opaque handles authorize only their "
    "operation; never request or expose raw tokens, worker/GPU/model internals, packets, logs, "
    "or transcripts. After facade restart, next_task with the same repo and task can recover a "
    "facade-owned claim. Live override needs manual out-of-band owner approval. Lost non-facade "
    "live claims require the owner's interactive todo recover force-release CLI, then ordinary "
    "next_task. This server cannot mint or self-approve either permission."
)


def create_server(backend: CodingWorkflowBackend | None = None) -> FastMCP:
    server = FastMCP("coding-workflow", instructions=SERVER_INSTRUCTIONS, log_level="ERROR")
    instance = backend

    def active_backend() -> CodingWorkflowBackend:
        nonlocal instance
        if instance is None:
            instance = CodingWorkflowBackend()
        return instance

    def invoke(method: str, *arguments: object) -> dict[str, object]:
        try:
            return getattr(active_backend(), method)(*arguments)
        except InvalidHandle:
            return {"status": "invalid_handle", "reason": "unknown_expired_or_inactive_capability"}
        except BackendError as error:
            result: dict[str, object] = {"status": "error", "reason": error.code}
            if error.diagnostic_id:
                result["diagnostic_id"] = error.diagnostic_id
            return result
        except Exception as error:  # No traceback or raw stderr crosses stdio.
            try:
                diagnostic_id = active_backend().store.write_diagnostic(type(error).__name__)
            except Exception:
                diagnostic_id = None
            result = {"status": "error", "reason": "unexpected_internal_failure"}
            if diagnostic_id:
                result["diagnostic_id"] = diagnostic_id
            return result

    @server.tool(
        description="Claim, resume, or manually-approved emergency-recover one todo task capsule.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def next_task(
        repo_root: str,
        task_id: str | None = None,
        recovery_approval: str | None = None,
    ) -> dict[str, object]:
        return invoke("next_task", repo_root, task_id, recovery_approval)

    @server.tool(
        description="Refresh bounded task, source, or action-worthy evidence context.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        structured_output=True,
    )
    def inspect_task(
        workflow_handle: str,
        focus: Literal["task", "source", "evidence"],
        target: str | None = None,
        intent: Literal["understand", "edit", "debug", "test", "review", "performance"] = "understand",
        budget_tokens: int = 2400,
    ) -> dict[str, object]:
        return invoke("inspect_task", workflow_handle, focus, target, intent, budget_tokens)

    @server.tool(
        description="Request optional nonblocking local assistance; continue on unavailable.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def delegate_task(
        workflow_handle: str,
        mode: Literal["auto", "readonly", "writable"],
        target: str | None = None,
    ) -> dict[str, object]:
        return invoke("delegate_task", workflow_handle, mode, target)

    @server.tool(
        description="Nonblockingly collect one previously returned delegation handle.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        structured_output=True,
    )
    def collect_delegation(delegation_handle: str) -> dict[str, object]:
        return invoke("collect_delegation", delegation_handle)

    @server.tool(
        description="Apply one authoritative todo completion, handoff, block, or release.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def finish_task(
        workflow_handle: str,
        action: Literal["complete", "handoff", "block", "release"],
        disposition: Literal[
            "implemented", "validated", "evaluated_not_promoted", "no_change_required", "superseded", "failed"
        ],
        note: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        return invoke("finish_task", workflow_handle, action, disposition, note, reason)

    return server
