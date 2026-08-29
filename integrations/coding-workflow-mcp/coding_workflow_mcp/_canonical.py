"""Load the canonical todo-orchestrator workflow package without side effects."""

from __future__ import annotations

from pathlib import Path

from .runtime_identity import (
    bind_canonical_runtime,
    locate_skills_root,
    project_runtime_context,
    validate_runtime,
)


_BOUND_RUNTIME = None


def skills_root() -> Path:
    return locate_skills_root()


def runtime_identity():
    global _BOUND_RUNTIME
    if _BOUND_RUNTIME is None:
        _BOUND_RUNTIME = bind_canonical_runtime()
    else:
        validate_runtime(_BOUND_RUNTIME)
    return _BOUND_RUNTIME


def protocol():
    identity = runtime_identity()
    from todo_orchestrator.workflow import WorkflowCapabilityLocator, WorkflowKernel, WorkflowProtocol
    from todo_orchestrator.models import TodoError

    def guard(repo_root: Path) -> None:
        try:
            validate_runtime(identity)
        except Exception as exc:
            if getattr(exc, "code", None) == "runtime_identity_mismatch":
                details = {
                    "expected": str(getattr(exc, "expected", identity.module_file)),
                    "observed": str(getattr(exc, "observed", "unknown")),
                    "canonical_skills_root": str(identity.skills_root),
                    "canonical_package_root": str(identity.package_root),
                    "runtime_fingerprint": identity.fingerprint,
                    "remediation": "restart the persistent workflow process using the canonical Skills runtime",
                }
                try:
                    context = project_runtime_context(repo_root, identity)
                    details.update({key: context[key] for key in ("project_uuid", "db_path")})
                except Exception:
                    pass
                raise TodoError("runtime_identity_mismatch", str(exc), details=details) from exc
            raise

    locator = WorkflowCapabilityLocator()
    return WorkflowProtocol(WorkflowKernel(locator=locator, runtime_guard=guard), locator)


def canonical_server():
    runtime_identity()
    from todo_orchestrator.workflow.mcp import create_server

    return create_server(protocol_factory=protocol)
