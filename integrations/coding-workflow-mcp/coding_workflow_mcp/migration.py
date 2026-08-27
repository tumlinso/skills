"""Idempotent repository routing and project-policy migration."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


START_MARKER = "<!-- coding-workflow:start -->"
END_MARKER = "<!-- coding-workflow:end -->"
ROUTING_SECTION = """<!-- coding-workflow:start -->
## Coding workflow

For substantial repository work, use `coding-workflow`.
Do not directly invoke todo-orchestrator, cpp-context-compiler, CUDA, or
local-coding-worker unless coding-workflow returns an explicit bounded fallback
authorization, the user explicitly requests maintenance, or coding-workflow
itself is being debugged.

Start with `next_task`. First-class Codex agents receive run lanes and roles.
Local workers are bounded children of one parent claim: they never claim project
todos, receive lanes or roles, communicate across lanes, join rendezvous, publish
project decisions or interfaces, or complete the parent task.
<!-- coding-workflow:end -->
"""


class MigrationError(RuntimeError):
    pass


def canonical_repo(repo: str | os.PathLike[str]) -> Path:
    result = subprocess.run(
        ["git", "-C", str(Path(repo).expanduser()), "rev-parse", "--show-toplevel"],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, shell=False,
    )
    if result.returncode:
        raise MigrationError("repo is not a Git worktree")
    return Path(result.stdout.strip()).resolve()


def _section_span(content: str) -> tuple[int, int] | None:
    start = content.find(START_MARKER)
    end = content.find(END_MARKER)
    if start < 0 and end < 0:
        return None
    if start < 0 or end < start or content.find(START_MARKER, start + 1) >= 0:
        raise MigrationError("AGENTS.md has malformed coding-workflow marker sections")
    finish = end + len(END_MARKER)
    while finish < len(content) and content[finish] == "\n" and finish < end + len(END_MARKER) + 2:
        finish += 1
    return start, finish


def _insert_near_top(content: str) -> str:
    heading = re.match(r"\A(#[^\n]*\n(?:\n)?)", content)
    position = heading.end() if heading else 0
    before, after = content[:position], content[position:]
    if before and not before.endswith("\n\n"):
        before += "\n"
    if after and not after.startswith("\n"):
        after = "\n" + after
    return before + ROUTING_SECTION + after


def _updated_agents(content: str, *, remove: bool) -> tuple[str, str]:
    span = _section_span(content)
    if remove:
        return (content if span is None else content[:span[0]] + content[span[1]:], "remove")
    if span is None:
        return _insert_near_top(content), "add"
    return _insert_near_top(content[:span[0]] + content[span[1]:]), "refresh"


def _updated_project(path: Path, *, remove: bool) -> tuple[str | None, bool]:
    if not path.exists():
        return None, False
    try:
        project = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError("project identity is not valid JSON") from exc
    if not isinstance(project, dict) or not isinstance(project.get("configuration"), dict):
        raise MigrationError("project identity has no configuration object")
    configuration = project["configuration"]
    before = dict(configuration)
    if remove:
        configuration.pop("workflow_front_door", None)
    else:
        configuration["workflow_front_door"] = "coding-workflow"
    return json.dumps(project, indent=2, sort_keys=True) + "\n", configuration != before


def _atomic_write(path: Path, content: str) -> None:
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _apply_all(changes: list[tuple[Path, str]]) -> None:
    originals = [(path, path.read_text(encoding="utf-8") if path.exists() else None) for path, _ in changes]
    try:
        for path, content in changes:
            _atomic_write(path, content)
    except Exception:
        for path, content in originals:
            if content is not None:
                _atomic_write(path, content)
            elif path.exists():
                path.unlink()
        raise


def migrate(repo: str | os.PathLike[str], *, apply: bool = False, remove: bool = False) -> dict[str, Any]:
    root = canonical_repo(repo)
    agents = root / "AGENTS.md"
    project_path = root / ".todo-orchestrator" / "project.json"
    original_agents = agents.read_text(encoding="utf-8") if agents.exists() else ""
    updated_agents, operation = _updated_agents(original_agents, remove=remove)
    updated_project, project_changed = _updated_project(project_path, remove=remove)
    changes = []
    if updated_agents != original_agents:
        changes.append((agents, updated_agents))
    if updated_project is not None and project_changed:
        changes.append((project_path, updated_project))
    if apply and changes:
        _apply_all(changes)
    changed = bool(changes)
    return {
        "status": "applied" if apply and changed else "unchanged" if not changed else "dry_run",
        "repo": str(root),
        "agents_file": "AGENTS.md",
        "project_file": ".todo-orchestrator/project.json" if project_path.exists() else None,
        "operation": operation,
        "changed": changed,
        "workflow_front_door": None if remove else "coding-workflow",
        "classification": {
            "preserve": ["user guidance", "task plans", "task IDs", "gates", "architectural constraints"],
            "maintenance": ["interactive todo maintenance", "explicit workflow self-debugging"],
        },
    }
