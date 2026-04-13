#!/usr/bin/env python3
"""Explicit cleanup for completed todo-orchestrator workstreams."""

from __future__ import annotations

import argparse
from pathlib import Path

from todo_common import (
    PLACEHOLDER,
    ROOT_SECTION_ORDER,
    STATUS_SECTION_ORDER,
    WORKSTREAM_PLACEHOLDER,
    clear_placeholder,
    default_root_doc,
    default_status_doc,
    load_root_doc,
    load_status_doc,
    parse_workstream_entries,
    remove_status_entry,
    remove_workstream_entry,
    write_document,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean up completed todo ledgers.")
    parser.add_argument("--repo-root", default=".", help="Repository root that contains todos.md.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Show what cleanup would do without modifying files.")
    mode.add_argument("--apply", action="store_true", help="Delete completed workstream files and compact ledgers.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    root_doc = load_root_doc(repo_root)
    status_doc = load_status_doc(repo_root)
    entries = parse_workstream_entries(clear_placeholder(root_doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    unfinished = [entry["slug"] for entry in entries if entry["status"] != "done"]
    to_delete = [(entry["slug"], repo_root / entry["file"]) for entry in entries]

    print(f"Tracked workstreams: {len(entries)}")
    if unfinished:
        print("Cleanup blocked. Unfinished workstreams:")
        for slug in unfinished:
            print(f"- {slug}")
        return 1

    if to_delete:
        print("Cleanup targets:")
        for slug, path in to_delete:
            suffix = "" if path.exists() else " (file already missing)"
            print(f"- {slug} -> {path.relative_to(repo_root)}{suffix}")
    else:
        print("Cleanup targets: none")

    if not args.apply:
        print("Dry run only. Re-run with --apply to compact ledgers.")
        return 0

    for slug, path in to_delete:
        if path.exists():
            path.unlink()
        remove_workstream_entry(root_doc, slug)
        remove_status_entry(status_doc, slug)

    default_root = default_root_doc()
    root_doc.sections["Summary"] = default_root.sections["Summary"]
    root_doc.sections["Shared Assumptions"] = [PLACEHOLDER]
    root_doc.sections["Suggested Skills"] = [PLACEHOLDER]
    root_doc.sections["Useful Reference Files"] = [PLACEHOLDER]
    root_doc.sections["Workstreams"] = default_root.sections["Workstreams"]
    root_doc.sections["Global Blockers"] = [PLACEHOLDER]
    if to_delete:
        slugs = ", ".join(slug for slug, _ in to_delete)
        root_doc.sections["Progress Notes"] = [f"- Ran `todo-cleanup` and cleared completed workstreams: {slugs}."]
    else:
        root_doc.sections["Progress Notes"] = [PLACEHOLDER]
    root_doc.sections["Next Actions"] = default_root.sections["Next Actions"]
    root_doc.sections["Done Criteria"] = default_root.sections["Done Criteria"]
    write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)

    default_status = default_status_doc()
    status_doc.sections["Summary"] = default_status.sections["Summary"]
    status_doc.sections["Workstreams"] = default_status.sections["Workstreams"]
    status_doc.sections["Cleanup Status"] = [
        "- Cleanup mode is explicit only.",
        "- Safe to call `todo-cleanup`: yes, there are no tracked workstreams left.",
    ]
    write_document(repo_root / "todo-status.md", status_doc, STATUS_SECTION_ORDER)

    print("Cleanup complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
