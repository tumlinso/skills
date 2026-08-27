"""Load the canonical todo-orchestrator workflow package without side effects."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def skills_root() -> Path:
    configured = os.environ.get("CODING_WORKFLOW_SKILLS_ROOT")
    root = Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[3]
    package = root / "todo-orchestrator" / "todo_orchestrator"
    if not package.is_dir():
        raise RuntimeError("canonical todo-orchestrator package is unavailable")
    parent = str(package.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return root


def protocol():
    skills_root()
    from todo_orchestrator.workflow import WorkflowCapabilityLocator, WorkflowKernel, WorkflowProtocol

    locator = WorkflowCapabilityLocator()
    return WorkflowProtocol(WorkflowKernel(locator=locator), locator)


def canonical_server():
    skills_root()
    from todo_orchestrator.workflow.mcp import create_server

    return create_server(protocol_factory=protocol)
