"""Load the canonical todo-orchestrator workflow package without side effects."""

from __future__ import annotations

import os
from pathlib import Path
import json
import sys


def _locator_file() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser()
    return data_home / "coding-workflow-mcp" / "skills-root.json"


def skills_root() -> Path:
    configured = os.environ.get("CODING_WORKFLOW_SKILLS_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
    elif _locator_file().is_file():
        locator = json.loads(_locator_file().read_text(encoding="utf-8"))
        root = Path(str(locator["skills_root"])).expanduser().resolve()
    else:
        root = Path(__file__).resolve().parents[3]
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
