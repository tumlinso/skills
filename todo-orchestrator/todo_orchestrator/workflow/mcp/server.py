"""Exact six-tool MCP surface over the in-process workflow protocol."""

from __future__ import annotations

import json
import secrets
from typing import Callable, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from ...models import TodoError
from ..foundation import PROTOCOL_VERSION
from ..protocol import WorkflowProtocol


def _bounded_error_details(details: object, *, budget_bytes: int = 1024) -> object:
    """Preserve useful typed details without turning an error envelope into a dump."""
    encoded = lambda value: json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    if len(encoded({"details": details})) <= budget_bytes:
        return details
    if isinstance(details, dict):
        result: dict[str, object] = {}
        for key in sorted(details):
            candidate = {**result, str(key): details[key]}
            if len(encoded({"details": candidate})) > budget_bytes:
                continue
            result = candidate
        result["truncated"] = True
        return result
    return {"truncated": True}


SERVER_INSTRUCTIONS = (
    "For substantial repository work, use coding-workflow as the only ordinary workflow protocol. "
    "Start with next_task. Do not invoke todo-orchestrator, cpp-context-compiler, CUDA, or "
    "local-coding-worker directly unless coding-workflow returns an explicit bounded fallback "
    "authorization, the user requests maintenance, or coding-workflow itself is being debugged. "
    "First-class Codex agents receive durable run lanes and roles. Local workers are subordinate "
    "bounded children of one parent claim: they never claim todos, receive lanes or roles, message "
    "peer lanes, publish decisions or interfaces, arrive at rendezvous, or complete the parent. "
    "Use coordinate_task for synchronization, messages, arrivals, interfaces, gate execution, "
    "integration requests, and explicit child acceptance or rejection. Delegation is nonblocking; "
    "continue immediately when unavailable and never poll. Opaque handles are the only model-facing "
    "authorization. Owner recovery is out of band through coding-workflow-admin."
)


def create_server(
    protocol: WorkflowProtocol | None = None,
    *,
    protocol_factory: Callable[[], WorkflowProtocol] | None = None,
    diagnostic_factory: Callable[[], str] | None = None,
) -> FastMCP:
    """Construct the server without opening a repo, DB, process, model, or GPU."""

    server = FastMCP("coding-workflow", instructions=SERVER_INSTRUCTIONS, log_level="ERROR")
    instance = protocol

    def active_protocol() -> WorkflowProtocol:
        nonlocal instance
        if instance is None:
            if protocol_factory is None:
                raise TodoError("workflow_kernel_unconfigured", "Canonical WorkflowKernel is not configured")
            instance = protocol_factory()
        return instance

    def diagnostic_id() -> str:
        return diagnostic_factory() if diagnostic_factory is not None else "diag_" + secrets.token_urlsafe(12)

    def invoke(method: str, **arguments: object) -> dict[str, object]:
        try:
            return getattr(active_protocol(), method)(**arguments)
        except Exception as error:
            code = getattr(error, "code", None)
            if isinstance(code, str) and code:
                result: dict[str, object] = {
                    "protocol_version": PROTOCOL_VERSION,
                    "status": "attention_required",
                    "reason": code,
                    "allowed_actions": [],
                    "recommended_next_call": None,
                    "warnings": [],
                }
                details = getattr(error, "details", None)
                if details is not None:
                    result["details"] = _bounded_error_details(details)
                message = getattr(error, "message", None)
                if isinstance(message, str) and message:
                    result["message"] = message[:512]
                if code == "runtime_identity_mismatch" and isinstance(details, dict):
                    result["compatibility"] = details
                if code.startswith(("runtime_", "workflow_owner_", "owner_")):
                    result["required_decision"] = "repair the reported runtime or owner binding before retrying"
                return result
            return {
                "protocol_version": PROTOCOL_VERSION,
                "status": "attention_required",
                "reason": "unexpected_internal_failure",
                "diagnostic_id": diagnostic_id(),
                "allowed_actions": [],
                "recommended_next_call": None,
                "warnings": [],
            }

    @server.tool(
        description="Atomically resume or claim a first-class run lane and its current task.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def next_task(
        repo_root: str, task_id: str | None = None, run_id: str | None = None
    ) -> dict[str, object]:
        return invoke("next_task", repo_root=repo_root, task_id=task_id, run_id=run_id)

    @server.tool(
        description="Read one bounded, scope-aware workflow or source context target.",
        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True),
        structured_output=True,
    )
    def inspect_task(
        workflow_handle: str,
        kind: Literal[
            "task", "source", "evidence", "run", "lane", "decision", "messages",
            "rendezvous", "workspace", "integration", "context_fragment",
        ],
        target: str | None = None,
        budget_bytes: int = 8192,
    ) -> dict[str, object]:
        return invoke(
            "inspect_task",
            workflow_handle=workflow_handle,
            kind=kind,
            target=target,
            budget_bytes=budget_bytes,
        )

    @server.tool(
        description="Perform one role- and scope-validated typed coordination action.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def coordinate_task(
        workflow_handle: str,
        action: Literal[
            "sync", "fork", "message", "answer", "arrive", "publish_interface",
            "publish_context", "run_gates", "bind_required_gates", "request_integration", "accept_child", "reject_child",
        ],
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return invoke(
            "coordinate_task", workflow_handle=workflow_handle, action=action, payload=payload
        )

    @server.tool(
        description="Opportunistically start one bounded subordinate local-worker child.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def delegate_task(
        workflow_handle: str,
        delegated_objective: str,
        mode: Literal["auto", "readonly", "writable"] = "auto",
        source_targets: list[str] | None = None,
    ) -> dict[str, object]:
        return invoke(
            "delegate_task",
            workflow_handle=workflow_handle,
            delegated_objective=delegated_objective,
            mode=mode,
            source_targets=source_targets,
        )

    @server.tool(
        description="Nonblockingly collect a candidate result from one subordinate child.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def collect_delegation(delegation_handle: str) -> dict[str, object]:
        return invoke("collect_delegation", delegation_handle=delegation_handle)

    @server.tool(
        description="Complete, hand off, block, or release the first-class parent task.",
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False),
        structured_output=True,
    )
    def finish_task(
        workflow_handle: str,
        action: Literal["complete", "handoff", "block", "release"],
        disposition: str | None = None,
        note: str | None = None,
        reason: str | None = None,
    ) -> dict[str, object]:
        return invoke(
            "finish_task",
            workflow_handle=workflow_handle,
            action=action,
            disposition=disposition,
            note=note,
            reason=reason,
        )

    return server
