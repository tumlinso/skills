#!/usr/bin/env python3
"""Update root or workstream todo ledgers."""

from __future__ import annotations

import argparse
from pathlib import Path

from todo_common import (
    ROOT_SECTION_ORDER,
    WORKSTREAM_SECTION_ORDER,
    append_section_bullets,
    append_structured_values,
    ensure_root_files,
    ensure_workstream_file,
    load_root_doc,
    load_workstream_doc,
    normalize_slug,
    set_section_text,
    set_task_status,
    upsert_task,
    upsert_workstream_entry,
    write_document,
)


def split_pairs(values: list[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for value in values:
        head, _, tail = value.partition("::")
        pairs.append((head.strip(), tail.strip()))
    return pairs


def apply_text_list(doc, section: str, values: list[str]) -> None:
    if values:
        append_section_bullets(doc, section, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Update structured sections in todos.md or a workstream ledger.")
    parser.add_argument("--repo-root", default=".", help="Repository root that should contain todos.md.")
    parser.add_argument("--workstream", help="Optional workstream slug to update instead of root todos.md.")
    parser.add_argument("--objective", help="Summary or objective for the workstream entry.")
    parser.add_argument("--owner", default="unassigned", help="Owner or agent label for the workstream entry.")
    parser.add_argument(
        "--status",
        choices=["planned", "in_progress", "blocked", "done"],
        help="Workstream status used in the root index.",
    )
    parser.add_argument("--summary", help="Replacement text for the Summary section.")
    parser.add_argument("--planning-note", action="append", default=[], help="Bullet to append to Planning Notes.")
    parser.add_argument("--assumption", action="append", default=[], help="Bullet to append to Assumptions.")
    parser.add_argument("--shared-assumption", action="append", default=[], help="Bullet to append to Shared Assumptions.")
    parser.add_argument("--plan-step", action="append", default=[], help="Bullet to append to Plan.")
    parser.add_argument("--task", action="append", default=[], help="Task to add if it does not already exist.")
    parser.add_argument(
        "--task-status",
        action="append",
        default=[],
        help="Update an existing task using task::status where status is one of space, ~, x, !.",
    )
    parser.add_argument("--blocker", action="append", default=[], help="Bullet to append to Blockers.")
    parser.add_argument("--global-blocker", action="append", default=[], help="Bullet to append to Global Blockers.")
    parser.add_argument("--suggested-skill", action="append", default=[], help="Entry in the form name::why.")
    parser.add_argument("--useful-reference", action="append", default=[], help="Entry in the form path::why.")
    parser.add_argument("--progress-note", action="append", default=[], help="Bullet to append to Progress Notes.")
    parser.add_argument("--next-action", action="append", default=[], help="Bullet to append to Next Actions.")
    parser.add_argument("--done-criterion", action="append", default=[], help="Bullet to append to Done Criteria.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    ensure_root_files(repo_root)

    if args.workstream:
        slug = normalize_slug(args.workstream)
        objective = args.objective or slug.replace("-", " ")
        ensure_workstream_file(
            repo_root,
            slug=slug,
            objective=objective,
            status=args.status or "planned",
            owner=args.owner,
        )
        doc = load_workstream_doc(repo_root, slug, objective)
        if args.summary:
            set_section_text(doc, "Summary", args.summary)
        apply_text_list(doc, "Planning Notes", args.planning_note)
        apply_text_list(doc, "Assumptions", args.assumption)
        apply_text_list(doc, "Plan", args.plan_step)
        for task in args.task:
            upsert_task(doc, task, status=" ")
        for value in args.task_status:
            task_text, _, task_status = value.partition("::")
            if task_text.strip():
                set_task_status(doc, task_text.strip(), task_status.strip() or " ")
        apply_text_list(doc, "Blockers", args.blocker)
        append_structured_values(doc, "Suggested Skills", split_pairs(args.suggested_skill))
        append_structured_values(doc, "Useful Reference Files", split_pairs(args.useful_reference))
        apply_text_list(doc, "Progress Notes", args.progress_note)
        apply_text_list(doc, "Next Actions", args.next_action)
        apply_text_list(doc, "Done Criteria", args.done_criterion)
        write_document(repo_root / "todos" / f"{slug}.md", doc, WORKSTREAM_SECTION_ORDER)

        root_doc = load_root_doc(repo_root)
        upsert_workstream_entry(root_doc, slug, objective, status=args.status or "planned", owner=args.owner)
        if args.shared_assumption:
            apply_text_list(root_doc, "Shared Assumptions", args.shared_assumption)
        if args.global_blocker:
            apply_text_list(root_doc, "Global Blockers", args.global_blocker)
        if args.progress_note:
            apply_text_list(root_doc, "Progress Notes", args.progress_note)
        if args.next_action:
            apply_text_list(root_doc, "Next Actions", args.next_action)
        if args.done_criterion:
            apply_text_list(root_doc, "Done Criteria", args.done_criterion)
        if args.suggested_skill:
            append_structured_values(root_doc, "Suggested Skills", split_pairs(args.suggested_skill))
        if args.useful_reference:
            append_structured_values(root_doc, "Useful Reference Files", split_pairs(args.useful_reference))
        write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)
        print(repo_root / "todos" / f"{slug}.md")
        return 0

    doc = load_root_doc(repo_root)
    if args.summary:
        set_section_text(doc, "Summary", args.summary)
    apply_text_list(doc, "Shared Assumptions", args.shared_assumption or args.assumption)
    apply_text_list(doc, "Global Blockers", args.global_blocker or args.blocker)
    append_structured_values(doc, "Suggested Skills", split_pairs(args.suggested_skill))
    append_structured_values(doc, "Useful Reference Files", split_pairs(args.useful_reference))
    apply_text_list(doc, "Progress Notes", args.progress_note)
    apply_text_list(doc, "Next Actions", args.next_action)
    apply_text_list(doc, "Done Criteria", args.done_criterion)
    write_document(repo_root / "todos.md", doc, ROOT_SECTION_ORDER)
    print(repo_root / "todos.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
