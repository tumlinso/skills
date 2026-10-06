#!/usr/bin/env python3
"""Compatibility interface for authored CUDA skill navigation.

Natural-language guidance always returns the authored skill entrypoint. The
agent reads that route and chooses references using the task and evidence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def corpus_files(skill_root: Path) -> list[Path]:
    """List reference Markdown covered by the guidance manifest."""
    references = skill_root / "references"
    if not references.is_dir():
        return []
    return sorted(path for path in references.rglob("*.md") if path.is_file())


def manifest(skill_root: Path) -> dict[str, object]:
    files = []
    for path in [skill_root / "SKILL.md", *corpus_files(skill_root)]:
        files.append({
            "path": path.relative_to(skill_root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        })
    return {"schema_version": 1, "files": files}


def validate_manifest(skill_root: Path, payload: dict[str, object]) -> list[str]:
    """Report missing or hash-mismatched files without reading outside root."""
    problems = []
    root = skill_root.resolve()
    for item in payload.get("files", []):
        relative = Path(str(item["path"]))
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            problems.append(f"outside-root:{item['path']}")
            continue
        if not path.exists():
            problems.append(f"missing:{item['path']}")
        elif sha256(path) != item["sha256"]:
            problems.append(f"hash:{item['path']}")
    return problems


def _is_instruction_markdown(skill_root: Path, path: Path) -> bool:
    """Limit exact reads to the skill entrypoint and its reference documents."""
    relative = path.relative_to(skill_root).as_posix()
    return relative == "SKILL.md" or (
        relative.startswith("references/") and relative.endswith(".md")
    )


def _full_document(skill_root: Path, query: str) -> dict[str, Any]:
    relative = query[5:].strip()
    if not relative:
        raise ValueError("full: requires a path to instruction Markdown")
    root = skill_root.resolve()
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("full: path must stay inside the CUDA skill root") from error
    if not _is_instruction_markdown(root, path) or not path.is_file():
        raise ValueError("full: only SKILL.md or references/**/*.md can be read")
    text = path.read_text(encoding="utf-8")
    return {
        "kind": "collected-guidance",
        "query": query,
        "navigation_mode": "exact-authored-document",
        "authority_model": "agent-semantic-router",
        "token_estimate": max(1, len(text) // 4),
        "sections": [{
            "path": path.relative_to(root).as_posix(),
            "heading": "<full-document>",
            "line_start": 1,
            "line_end": len(text.splitlines()),
            "content_hash": sha256(path),
            "text": text,
        }],
    }


def retrieve(
    skill_root: Path,
    query: str,
    *,
    limit: int = 3,
    token_budget: int = 900,
) -> dict[str, object]:
    """Return the authored entrypoint for any natural-language query.

    ``limit`` and ``token_budget`` remain accepted for callers of the former
    search API. Natural-language queries receive a stable pointer to the
    authored route; they never trigger query-based route selection.
    """
    del limit  # Compatibility parameter; never a route-selection control.
    if query.startswith("full:"):
        return _full_document(skill_root, query)

    return {
        "kind": "collected-guidance",
        "query": query,
        "navigation_mode": "authored-entrypoint",
        "authority_model": "agent-semantic-router",
        "token_estimate": 0,
        "sections": [],
        "navigation_pointer": "SKILL.md",
    }
