"""Coding-workflow protocol v2 and its narrow in-process kernel port."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, Sequence

from ..models import TodoError
from .capabilities import (
    AuthorizedCapability,
    WorkflowCapabilityStore,
)
from .foundation import (
    COORDINATE_TASK_BUDGET_BYTES,
    COORDINATION_ACTIONS,
    DELEGATION_RESULT_BUDGET_BYTES,
    FINISH_TASK_BUDGET_BYTES,
    NEXT_TASK_BUDGET_BYTES,
    PROTOCOL_VERSION,
    require_bounded_payload,
)


TOOL_NAMES = (
    "next_task",
    "inspect_task",
    "coordinate_task",
    "delegate_task",
    "collect_delegation",
    "finish_task",
)
STATUSES = frozenset({
    "claimed",
    "resumed",
    "idle",
    "blocked",
    "attention_required",
    "context_stale",
    "recovery_needed",
    "fallback_authorized",
})
INSPECTION_KINDS = frozenset({
    "task", "source", "evidence", "run", "lane", "decision", "messages",
    "rendezvous", "workspace", "integration",
})
FINISH_ACTIONS = frozenset({"complete", "handoff", "block", "release"})

_PRIVATE_KEYS = frozenset({
    "token", "claim_token", "session_token", "child_token", "worker_token",
    "approval_token", "recovery_approval", "gpu_identifier", "model_endpoint",
    "packet", "packet_body", "child_packet", "log", "logs", "transcript", "transcripts",
    "stdout", "stderr", "traceback", "capability_lineage", "child_lineage",
})


class WorkflowKernelPort(Protocol):
    """Direct in-process seam implemented by the shared WorkflowKernel in WFU-20.

    ``next_task`` returns a handle staged in the same transaction as its claim
    and dispatch. ``delegate_task`` does the same for child creation. A terminal
    ``finish_task`` must stage family revocation in its completion transaction.
    The protocol verifies these postconditions rather than performing a second
    semantic mutation.
    """

    def next_task(self, *, repo_root: str, task_id: str | None) -> Mapping[str, Any]: ...
    def inspect_task(
        self, capability: AuthorizedCapability, *, kind: str, target: str | None, budget_bytes: int
    ) -> Mapping[str, Any]: ...
    def coordinate_task(
        self, capability: AuthorizedCapability, *, action: str, payload: Mapping[str, Any]
    ) -> Mapping[str, Any]: ...
    def delegate_task(
        self, capability: AuthorizedCapability, *, objective: str, mode: str
    ) -> Mapping[str, Any]: ...
    def collect_delegation(self, capability: AuthorizedCapability) -> Mapping[str, Any]: ...
    def finish_task(
        self,
        capability: AuthorizedCapability,
        *,
        action: str,
        disposition: str | None,
        note: str | None,
        reason: str | None,
    ) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class FallbackAuthorization:
    specialized_skill: str
    permitted_operation: str
    reason: str
    scope: Mapping[str, Any]
    access: Literal["read_only", "mutating"]

    def as_dict(self) -> dict[str, Any]:
        if self.specialized_skill not in {"todo-orchestrator", "cpp-context-compiler", "cuda", "local-coding-worker"}:
            raise TodoError("invalid_fallback_authorization", "Unknown specialized skill")
        if self.access not in {"read_only", "mutating"}:
            raise TodoError("invalid_fallback_authorization", "Fallback access mode is invalid")
        if not self.permitted_operation or not self.reason or not self.scope:
            raise TodoError("invalid_fallback_authorization", "Fallback permission must be bounded")
        return {
            "specialized_skill": self.specialized_skill,
            "permitted_operation": self.permitted_operation,
            "reason": self.reason,
            "scope": dict(self.scope),
            "access": self.access,
        }


_ACTION_SCHEMAS: dict[str, tuple[frozenset[str], frozenset[str]]] = {
    "sync": (frozenset(), frozenset({"cursor", "known_fragments"})),
    "fork": (frozenset({"tasks"}), frozenset({"tasks", "role", "workspace_mode"})),
    "message": (
        frozenset({"kind", "payload", "recipients"}),
        frozenset({"kind", "payload", "recipients", "references", "blocking"}),
    ),
    "answer": (frozenset({"question_id", "payload"}), frozenset({"question_id", "payload", "references"})),
    "arrive": (
        frozenset({"rendezvous_id", "summary"}),
        frozenset({"rendezvous_id", "summary", "artifact", "interfaces", "evidence", "warnings", "context_version"}),
    ),
    "publish_interface": (
        frozenset({"interface_id", "version", "content_hash"}),
        frozenset({"interface_id", "version", "content_hash", "evidence"}),
    ),
    "run_gates": (frozenset(), frozenset({"required"})),
    "request_integration": (
        frozenset({"artifacts"}),
        frozenset({"artifacts", "integration_task_id", "summary"}),
    ),
    "accept_child": (
        frozenset({"child_execution_id"}),
        frozenset({"child_execution_id", "result_id", "summary", "publish"}),
    ),
    "reject_child": (
        frozenset({"child_execution_id", "reason"}),
        frozenset({"child_execution_id", "result_id", "reason"}),
    ),
}


def _validate_action(action: str, payload: Mapping[str, Any]) -> None:
    if action not in COORDINATION_ACTIONS:
        raise TodoError("invalid_coordination_action", "Coordination action is not supported")
    required, allowed = _ACTION_SCHEMAS[action]
    missing = required - set(payload)
    extra = set(payload) - allowed
    if missing or extra:
        raise TodoError(
            "invalid_coordination_payload",
            "Coordination payload does not match its action schema",
            details={"missing": sorted(missing), "extra": sorted(extra)},
        )


def _public(value: object) -> object:
    """Recursively remove internal secrets and unbounded diagnostics."""
    if isinstance(value, Mapping):
        return {
            str(key): _public(item)
            for key, item in value.items()
            if str(key).lower() not in _PRIVATE_KEYS
            and not str(key).lower().endswith("_token")
            and not str(key).lower().endswith("_secret")
        }
    if isinstance(value, (list, tuple)):
        return [_public(item) for item in value]
    return value


def envelope(
    status: str,
    payload: Mapping[str, Any] | None = None,
    *,
    allowed_actions: Sequence[str] = (),
    recommended_next_call: str | None = None,
    budget_bytes: int = NEXT_TASK_BUDGET_BYTES,
) -> dict[str, Any]:
    if status not in STATUSES:
        raise TodoError("invalid_workflow_status", f"Protocol status is not stable: {status}")
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "status": status,
        **dict(_public(payload or {})),
        "allowed_actions": list(allowed_actions),
        "recommended_next_call": recommended_next_call,
    }
    require_bounded_payload(result, limit=budget_bytes, code="workflow_response_too_large")
    return result


def _stable_status(internal: dict[str, Any], default: str) -> str:
    raw = str(internal.pop("status", default))
    if raw in STATUSES:
        return raw
    internal["operation_status"] = raw
    return {
        "delegated": "claimed",
        "running": "idle",
        "candidate_available": "claimed",
        "accepted": "claimed",
        "completed": "claimed",
        "current": "claimed",
        "available": "claimed",
        "passed": "claimed",
        "finished": "idle",
        "local_unavailable": "fallback_authorized",
        "not_eligible": "fallback_authorized",
    }.get(raw, "attention_required")


def _add_identity(internal: dict[str, Any], capability: AuthorizedCapability) -> None:
    lineage = capability.lineage
    internal.setdefault("task_id", lineage.task_id)
    if lineage.capability_class == "first_class":
        internal.setdefault("run_id", lineage.run_id)
        internal.setdefault("lane_id", lineage.lane_id)
        internal.setdefault("role", lineage.role)
    else:
        internal.setdefault("child_execution_id", lineage.child_execution_id)


class WorkflowProtocol:
    """Capability-enforcing model boundary over one in-process kernel port."""

    def __init__(self, port: WorkflowKernelPort, capabilities: WorkflowCapabilityStore):
        self.port = port
        self.capabilities = capabilities

    def next_task(self, *, repo_root: str, task_id: str | None = None) -> dict[str, Any]:
        internal = dict(self.port.next_task(repo_root=repo_root, task_id=task_id))
        status = str(internal.get("status", "claimed"))
        if status in {"claimed", "resumed"}:
            handle = internal.get("workflow_handle")
            if not isinstance(handle, str):
                raise TodoError(
                    "workflow_kernel_contract_error",
                    "Claim transaction omitted its atomically issued workflow capability",
                )
            authorized = self.capabilities.resolve(
                handle, required_operation="inspect_task", expected_class="first_class"
            )
            internal["capability_incarnation"] = authorized.lineage.incarnation
        allowed = internal.pop("allowed_actions", ["inspect_task", "coordinate_task", "delegate_task", "finish_task"] if status in {"claimed", "resumed"} else [])
        recommended = internal.pop("recommended_next_call", "inspect_task" if status in {"claimed", "resumed"} else "next_task")
        return envelope(status, internal, allowed_actions=allowed, recommended_next_call=recommended)

    def inspect_task(
        self,
        *,
        workflow_handle: str,
        kind: str,
        target: str | None = None,
        budget_bytes: int = 8 * 1024,
    ) -> dict[str, Any]:
        if kind not in INSPECTION_KINDS:
            raise TodoError("invalid_inspection_kind", "Inspection kind is not supported")
        if budget_bytes < 512 or budget_bytes > 64 * 1024:
            raise TodoError("invalid_inspection_budget", "Inspection budget must be 512..65536 bytes")
        capability = self.capabilities.resolve(
            workflow_handle, required_operation="inspect_task", expected_class="first_class"
        )
        internal = dict(self.port.inspect_task(capability, kind=kind, target=target, budget_bytes=budget_bytes))
        _add_identity(internal, capability)
        status = _stable_status(internal, "context_stale" if internal.get("changed_fragments") else "claimed")
        recommended = str(internal.pop("recommended_next_call", "coordinate_task"))
        return envelope(
            status,
            internal,
            allowed_actions=["inspect_task", "coordinate_task", "delegate_task", "finish_task"],
            recommended_next_call=recommended,
            budget_bytes=budget_bytes,
        )

    def coordinate_task(
        self, *, workflow_handle: str, action: str, payload: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        body = dict(payload or {})
        _validate_action(action, body)
        capability = self.capabilities.resolve(
            workflow_handle,
            required_operation=f"coordinate:{action}",
            expected_class="first_class",
        )
        internal = dict(self.port.coordinate_task(capability, action=action, payload=body))
        _add_identity(internal, capability)
        status = _stable_status(internal, "claimed")
        recommended = str(internal.pop("recommended_next_call", "finish_task" if action == "run_gates" else "coordinate_task"))
        return envelope(
            status,
            internal,
            allowed_actions=["inspect_task", "coordinate_task", "delegate_task", "finish_task"],
            recommended_next_call=recommended,
            budget_bytes=COORDINATE_TASK_BUDGET_BYTES,
        )

    def delegate_task(
        self, *, workflow_handle: str, delegated_objective: str, mode: str = "auto"
    ) -> dict[str, Any]:
        if mode not in {"auto", "readonly", "writable"}:
            raise TodoError("invalid_delegation_mode", "Delegation mode is not supported")
        capability = self.capabilities.resolve(
            workflow_handle, required_operation="delegate_task", expected_class="first_class"
        )
        internal = dict(self.port.delegate_task(capability, objective=delegated_objective, mode=mode))
        _add_identity(internal, capability)
        raw_status = str(internal.get("status", "attention_required"))
        status = _stable_status(internal, "attention_required")
        if status == "fallback_authorized":
            authorization = internal.get("fallback_authorization")
            required = {"specialized_skill", "permitted_operation", "reason", "scope", "access"}
            if not isinstance(authorization, Mapping) or set(authorization) != required:
                status = "attention_required"
                internal.pop("fallback_authorization", None)
                internal["warnings"] = ["specialized fallback was not safely bounded"]
            else:
                internal["fallback_authorization"] = FallbackAuthorization(
                    specialized_skill=str(authorization["specialized_skill"]),
                    permitted_operation=str(authorization["permitted_operation"]),
                    reason=str(authorization["reason"]),
                    scope=dict(authorization["scope"]) if isinstance(authorization["scope"], Mapping) else {},
                    access=str(authorization["access"]),  # type: ignore[arg-type]
                ).as_dict()
        if raw_status == "delegated":
            handle = internal.get("delegation_handle")
            if not isinstance(handle, str):
                raise TodoError(
                    "workflow_kernel_contract_error",
                    "Delegation transaction omitted its atomically issued child capability",
                )
            child = self.capabilities.resolve(
                handle, required_operation="collect_delegation", expected_class="child"
            )
            if child.lineage.claim_id != capability.lineage.claim_id or child.lineage.task_id != capability.lineage.task_id:
                raise TodoError("child_parent_claim_mismatch", "Delegation handle escaped its parent claim")
        return envelope(
            status,
            internal,
            allowed_actions=["collect_delegation"] if raw_status == "delegated" else ["inspect_task", "coordinate_task", "finish_task"],
            recommended_next_call="collect_delegation" if raw_status == "delegated" else "coordinate_task",
            budget_bytes=DELEGATION_RESULT_BUDGET_BYTES,
        )

    def collect_delegation(self, *, delegation_handle: str) -> dict[str, Any]:
        capability = self.capabilities.resolve(
            delegation_handle, required_operation="collect_delegation", expected_class="child"
        )
        internal = dict(self.port.collect_delegation(capability))
        _add_identity(internal, capability)
        # Candidate child results are never authoritative parent completion.
        internal["parent_task_completed"] = False
        status = _stable_status(internal, "attention_required")
        return envelope(
            status,
            internal,
            allowed_actions=[],
            recommended_next_call="coordinate_task",
            budget_bytes=DELEGATION_RESULT_BUDGET_BYTES,
        )

    def finish_task(
        self,
        *,
        workflow_handle: str,
        action: str,
        disposition: str | None = None,
        note: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if action not in FINISH_ACTIONS:
            raise TodoError("invalid_finish_action", "Finish action is not supported")
        capability = self.capabilities.resolve(
            workflow_handle, required_operation="finish_task", expected_class="first_class"
        )
        internal = dict(self.port.finish_task(
            capability,
            action=action,
            disposition=disposition,
            note=note,
            reason=reason,
        ))
        _add_identity(internal, capability)
        status = _stable_status(internal, "idle")
        terminal = bool(internal.get("terminal", True))
        if terminal:
            try:
                self.capabilities.resolve(
                    workflow_handle, required_operation="inspect_task", expected_class="first_class"
                )
            except TodoError:
                pass
            else:
                raise TodoError(
                    "workflow_kernel_contract_error",
                    "Terminal finish did not atomically release its capability family",
                )
        return envelope(
            status,
            internal,
            allowed_actions=[] if terminal else ["next_task"],
            recommended_next_call="next_task",
            budget_bytes=FINISH_TASK_BUDGET_BYTES,
        )


def fallback_authorized(authorization: FallbackAuthorization) -> dict[str, Any]:
    return envelope(
        "fallback_authorized",
        {"fallback_authorization": authorization.as_dict()},
        allowed_actions=[],
        recommended_next_call=None,
    )
