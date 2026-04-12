#!/usr/bin/env python3
"""Summarize the canonical todo ledger."""

from __future__ import annotations

import argparse
from pathlib import Path

from todo_common import (
    PLACEHOLDER,
    WORKSTREAM_PLACEHOLDER,
    clear_placeholder,
    load_root_doc,
    parse_workstream_entries,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Summarize root todos.md.")
    parser.add_argument("--repo-root", default=".", help="Repository root that contains todos.md.")
    return parser


def first_real_line(lines: list[str]) -> str:
    cleaned = clear_placeholder(lines)
    return cleaned[0] if cleaned else "No summary recorded."


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    root_doc = load_root_doc(repo_root)

    summary = first_real_line(root_doc.sections.get("Summary", [PLACEHOLDER]))
    blockers = clear_placeholder(root_doc.sections.get("Global Blockers", [PLACEHOLDER]))
    next_actions = clear_placeholder(root_doc.sections.get("Next Actions", [PLACEHOLDER]))
    entries = parse_workstream_entries(clear_placeholder(root_doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))

    print(f"Summary: {summary}")
    if entries:
        print("Workstreams:")
        for entry in entries:
            print(f"- {entry['slug']} [{entry['status']}] -> {entry['objective']}")
    else:
        print("Workstreams: none")
    if blockers:
        print("Blockers:")
        for blocker in blockers:
            print(blocker)
    if next_actions:
        print("Next Actions:")
        for action in next_actions:
            print(action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
