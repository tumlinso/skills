"""Compatibility-preserving AGENTS.md routing migration."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


START_MARKER = "<!-- coding-workflow:start -->"
END_MARKER = "<!-- coding-workflow:end -->"
ROUTING_SECTION = """<!-- coding-workflow:start -->
## Coding workflow interface

- For substantial repository work, use the `coding-workflow` MCP server first.
- Call `next_task`, then use `inspect_task` only when bounded source/evidence context is needed.
- `delegate_task` is opportunistic. `local_unavailable` means continue directly in Codex; never wait for a GPU.
- Use `collect_delegation` only for a returned delegation handle and finish every claimed task with `finish_task`.
- Existing todo, ctxpp, CUDA, and local-worker CLIs remain valid fallback and debugging interfaces.
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
    if start < 0 or end < start:
        raise MigrationError("AGENTS.md has an incomplete coding-workflow marker section")
    finish = end + len(END_MARKER)
    for _ in range(2):
        if finish >= len(content) or content[finish] != "\n":
            break
        finish += 1
    return start, finish


def _insert_near_top(content: str) -> str:
    heading = re.match(r"\A(#[^\n]*\n(?:\n)?)", content)
    position = heading.end() if heading else 0
    before = content[:position]
    after = content[position:]
    if before and not before.endswith("\n\n"):
        before += "\n"
    if after and not after.startswith("\n"):
        after = "\n" + after
    return before + ROUTING_SECTION + after


def _atomic_write(path: Path, content: str) -> None:
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
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


def migrate(repo: str | os.PathLike[str], *, apply: bool = False, remove: bool = False) -> dict[str, Any]:
    root = canonical_repo(repo)
    agents = root / "AGENTS.md"
    content = agents.read_text(encoding="utf-8") if agents.exists() else ""
    span = _section_span(content)
    if remove:
        updated = content if span is None else content[:span[0]] + content[span[1]:]
        operation = "remove"
    elif span is None:
        updated = _insert_near_top(content)
        operation = "add"
    else:
        without_section = content[:span[0]] + content[span[1]:]
        updated = _insert_near_top(without_section)
        operation = "refresh"
    changed = updated != content
    if apply and changed:
        _atomic_write(agents, updated)
    direct_cli = [name for name in ("todo", "ctxpp", "CUDA", "local-worker") if name.lower() in content.lower()]
    return {
        "status": "applied" if apply and changed else "unchanged" if not changed else "dry_run",
        "repo": str(root),
        "agents_file": "AGENTS.md",
        "operation": operation,
        "changed": changed,
        "classification": {
            "preserve": ["task plans", "task IDs", "gates", "architectural constraints"],
            "fallback": [f"detailed {name} operating instructions" for name in direct_cli],
            "replace-later": ["verbose top-level routing prose"],
        },
    }
