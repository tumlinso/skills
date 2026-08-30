"""Bounded fallback adapters retained only through PCU-V1 cutover.

Every semantic operation below is delegated to Todo Orchestrator.  Project
Control is preferred by :mod:`coding_workflow_mcp.compat`; these functions are
entered only when the Project Control distribution is genuinely absent.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from .runtime_identity import bind_canonical_runtime, locate_skills_root, validate_runtime


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
    from todo_orchestrator.models import TodoError
    from todo_orchestrator.workflow import WorkflowCapabilityLocator, WorkflowKernel, WorkflowProtocol

    def guard(repo_root: Path) -> None:
        try:
            validate_runtime(identity)
        except Exception as error:
            details = {
                "expected": str(getattr(error, "expected", identity.package_source)),
                "observed": str(getattr(error, "observed", "unknown")),
                "canonical_skills_root": str(identity.skills_root),
                "canonical_package_root": str(identity.package_root),
                "runtime_fingerprint": identity.fingerprint,
                "remediation": "restart using the verified Project Control candidate",
            }
            raise TodoError("runtime_identity_mismatch", str(error), details=details) from error

    locator = WorkflowCapabilityLocator()
    return WorkflowProtocol(WorkflowKernel(locator=locator, runtime_guard=guard), locator)


def canonical_server():
    runtime_identity()
    from todo_orchestrator.workflow.mcp import create_server

    return create_server(protocol_factory=protocol)


def run_fallback_server() -> int:
    canonical_server().run(transport="stdio")
    return 0


def run_fallback_admin(argv: Sequence[str] | None = None) -> int:
    """Forward old installs directly to Todo's owner API until cutover."""

    runtime_identity()
    parser = argparse.ArgumentParser(prog="coding-workflow-admin")
    commands = parser.add_subparsers(dest="command", required=True)
    recover = commands.add_parser("recover", help="inspect and safely recover workflow ownership")
    recover.add_argument("--repo", required=True)
    recover.add_argument("--task")
    recover.add_argument("--reason", required=True)
    recover.add_argument("--inspect-only", action="store_true")
    arguments = parser.parse_args(argv)

    from todo_orchestrator.service import Service
    from todo_orchestrator.workflow.admin import inspect_owner_recovery, run_owner_recovery
    from todo_orchestrator.workflow.recovery import RecoveryEngine

    service = Service(arguments.repo, mutation_mode="self_debug")
    engine = RecoveryEngine(service.db, service.paths.repo_root, str(service.project["project_uuid"]))
    if arguments.inspect_only:
        result = inspect_owner_recovery(engine, arguments.task)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    run_owner_recovery(
        engine,
        database_path=service.paths.db_file,
        reason=arguments.reason,
        task_id=arguments.task,
    )
    return 0


__all__ = [
    "canonical_server", "protocol", "run_fallback_admin", "run_fallback_server",
    "runtime_identity", "skills_root",
]
