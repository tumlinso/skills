#!/usr/bin/env python3
"""Shared helpers for the todo-orchestrator scripts."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT_TITLE = "Active Objectives"
WORKSTREAM_TITLE = "Current Objective"
STATUS_TITLE = "Todo Status"

ROOT_SECTION_ORDER = [
    "Summary",
    "Shared Assumptions",
    "Suggested Skills",
    "Useful Reference Files",
    "Workstreams",
    "Global Blockers",
    "Progress Notes",
    "Next Actions",
    "Done Criteria",
]

WORKSTREAM_SECTION_ORDER = [
    "Summary",
    "Quick Start",
    "Planning Notes",
    "Assumptions",
    "Suggested Skills",
    "Useful Reference Files",
    "Plan",
    "Tasks",
    "Blockers",
    "Progress Notes",
    "Next Actions",
    "Done Criteria",
]

STATUS_SECTION_ORDER = [
    "Summary",
    "Workstreams",
    "Cleanup Status",
]

PLACEHOLDER = "_None recorded yet._"
WORKSTREAM_PLACEHOLDER = "_No active workstreams yet._"
STATUS_PLACEHOLDER = "_No tracked workstreams yet._"
TASK_PATTERN = re.compile(r"^- \[([ x~!])\] (.+)$")
WORKSTREAM_PATTERN = re.compile(
    r"^- `(?P<slug>[^`]+)` \| status: (?P<status>[^|]+) \| owner: (?P<owner>[^|]+) "
    r"\| file: `(?P<file>[^`]+)` \| objective: (?P<objective>.+)$"
)
STATUS_PATTERN = re.compile(
    r"^- `(?P<slug>[^`]+)` \| status: (?P<status>[^|]+) \| execution: (?P<execution>[^|]+) "
    r"\| owner: (?P<owner>[^|]+) \| file: `(?P<file>[^`]+)` \| next: (?P<next>.+)$"
)
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
AGENTS_START = "<!-- todo-orchestrator:start -->"
AGENTS_END = "<!-- todo-orchestrator:end -->"

DONE_STATUSES = {"done", "complete", "archived"}
PICKUP_READY_STATES = {"ready", "idle"}
DEFAULT_QUICK_START_LINES = [
    "- Why this stream exists: _Summarize the domain boundary and why it was split out._",
    "- In scope: _List the work this stream owns._",
    "- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._",
    "- Required skills: _List the exact repo-local skills to read before starting._",
    "- Required references: _List the exact repo-local references to read before starting._",
]


@dataclass
class MarkdownDoc:
    title: str
    preamble: list[str]
    sections: "OrderedDict[str, list[str]]"
    order: list[str]


def normalize_slug(value: str) -> str:
    slug = value.strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    return slug.strip("-") or "workstream"


def humanize_slug(value: str) -> str:
    text = value.replace("-", " ").strip()
    if not text:
        return "Workstream"
    return text[0].upper() + text[1:]


def normalize_text_lines(lines: Iterable[str]) -> list[str]:
    normalized = list(lines)
    while normalized and not normalized[0].strip():
        normalized.pop(0)
    while normalized and not normalized[-1].strip():
        normalized.pop()
    return normalized


def parse_markdown_document(text: str) -> MarkdownDoc:
    lines = text.splitlines()
    title = ""
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line:
            if line.startswith("# "):
                title = line[2:].strip()
                index += 1
            break
        index += 1

    preamble: list[str] = []
    sections: "OrderedDict[str, list[str]]" = OrderedDict()
    current_name: str | None = None
    current_lines: list[str] = []
    saw_section = False

    while index < len(lines):
        line = lines[index]
        if line.startswith("## "):
            if current_name is not None:
                sections[current_name] = normalize_text_lines(current_lines)
            elif preamble:
                preamble = normalize_text_lines(preamble)
            current_name = line[3:].strip()
            current_lines = []
            saw_section = True
        else:
            if saw_section and current_name is not None:
                current_lines.append(line)
            else:
                preamble.append(line)
        index += 1

    if current_name is not None:
        sections[current_name] = normalize_text_lines(current_lines)
    else:
        preamble = normalize_text_lines(preamble)

    return MarkdownDoc(title=title, preamble=preamble, sections=sections, order=list(sections.keys()))


def render_markdown_document(doc: MarkdownDoc, preferred_order: list[str]) -> str:
    lines: list[str] = [f"# {doc.title}", ""]
    if doc.preamble:
        lines.extend(normalize_text_lines(doc.preamble))
        lines.append("")

    seen: set[str] = set()
    section_names = [name for name in preferred_order if name in doc.sections]
    section_names.extend(name for name in doc.order if name in doc.sections and name not in seen and name not in section_names)

    for name in section_names:
        seen.add(name)
        lines.append(f"## {name}")
        section_lines = normalize_text_lines(doc.sections.get(name, []))
        if section_lines:
            lines.extend(section_lines)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def default_root_doc() -> MarkdownDoc:
    sections = OrderedDict(
        (
            ("Summary", ["Use this file as the canonical index for substantial multi-step work."]),
            ("Shared Assumptions", [PLACEHOLDER]),
            ("Suggested Skills", [PLACEHOLDER]),
            ("Useful Reference Files", [PLACEHOLDER]),
            ("Workstreams", [WORKSTREAM_PLACEHOLDER]),
            ("Global Blockers", [PLACEHOLDER]),
            ("Progress Notes", [PLACEHOLDER]),
            ("Next Actions", ["- Create or resume a workstream ledger under `todos/` for the next substantial task."]),
            ("Done Criteria", ["- Every active workstream in `todos/` is reflected here with a current status."]),
        )
    )
    return MarkdownDoc(title=ROOT_TITLE, preamble=[], sections=sections, order=list(sections.keys()))


def default_workstream_doc(objective: str) -> MarkdownDoc:
    sections = OrderedDict(
        (
            ("Summary", [objective or PLACEHOLDER]),
            ("Quick Start", DEFAULT_QUICK_START_LINES.copy()),
            ("Planning Notes", [PLACEHOLDER]),
            ("Assumptions", [PLACEHOLDER]),
            ("Suggested Skills", [PLACEHOLDER]),
            ("Useful Reference Files", [PLACEHOLDER]),
            ("Plan", [PLACEHOLDER]),
            ("Tasks", [PLACEHOLDER]),
            ("Blockers", [PLACEHOLDER]),
            ("Progress Notes", [PLACEHOLDER]),
            ("Next Actions", [PLACEHOLDER]),
            ("Done Criteria", [PLACEHOLDER]),
        )
    )
    return MarkdownDoc(title=WORKSTREAM_TITLE, preamble=[], sections=sections, order=list(sections.keys()))


def default_status_doc() -> MarkdownDoc:
    sections = OrderedDict(
        (
            (
                "Summary",
                [
                    "Use this file as the quick pickup register for `todos.md` workstreams.",
                    "- `ready`: planned work that can be started now.",
                    "- `claimed`: currently being written; choose another stream.",
                    "- `idle`: unfinished but resumable; safe to pick up.",
                    "- `closed`: completed or removed from pickup rotation.",
                ],
            ),
            ("Workstreams", [STATUS_PLACEHOLDER]),
            (
                "Cleanup Status",
                [
                    "- Cleanup mode is explicit only.",
                    "- Safe to call `todo-cleanup`: no, there are unfinished workstreams.",
                ],
            ),
        )
    )
    return MarkdownDoc(title=STATUS_TITLE, preamble=[], sections=sections, order=list(sections.keys()))


def ensure_sections(doc: MarkdownDoc, ordered_sections: list[str], placeholders: dict[str, list[str]] | None = None) -> MarkdownDoc:
    placeholders = placeholders or {}
    for name in ordered_sections:
        if name not in doc.sections:
            doc.sections[name] = placeholders.get(name, [PLACEHOLDER])
            doc.order.append(name)
    return doc


def write_document(path: Path, doc: MarkdownDoc, preferred_order: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown_document(doc, preferred_order), encoding="utf-8")


def load_root_doc(repo_root: Path) -> MarkdownDoc:
    path = repo_root / "todos.md"
    if path.exists():
        doc = parse_markdown_document(path.read_text(encoding="utf-8"))
    else:
        doc = default_root_doc()
    return ensure_sections(doc, ROOT_SECTION_ORDER, {"Workstreams": [WORKSTREAM_PLACEHOLDER]})


def load_workstream_doc(repo_root: Path, slug: str, objective: str = "") -> MarkdownDoc:
    path = repo_root / "todos" / f"{slug}.md"
    if path.exists():
        doc = parse_markdown_document(path.read_text(encoding="utf-8"))
    else:
        doc = default_workstream_doc(objective or humanize_slug(slug))
    return ensure_sections(doc, WORKSTREAM_SECTION_ORDER)


def load_status_doc(repo_root: Path) -> MarkdownDoc:
    path = repo_root / "todo-status.md"
    if path.exists():
        doc = parse_markdown_document(path.read_text(encoding="utf-8"))
    else:
        doc = default_status_doc()
    return ensure_sections(doc, STATUS_SECTION_ORDER, {"Workstreams": [STATUS_PLACEHOLDER]})


def clear_placeholder(lines: list[str], placeholder: str = PLACEHOLDER) -> list[str]:
    normalized = normalize_text_lines(lines)
    if normalized in ([placeholder], [WORKSTREAM_PLACEHOLDER], [STATUS_PLACEHOLDER]):
        return []
    return normalized


def append_unique_bullets(lines: list[str], values: Iterable[str]) -> list[str]:
    current = clear_placeholder(lines)
    for value in values:
        item = value.strip()
        if not item:
            continue
        bullet = item if item.startswith("- ") else f"- {item}"
        if bullet not in current:
            current.append(bullet)
    return current or [PLACEHOLDER]


def set_section_text(doc: MarkdownDoc, section: str, text: str) -> None:
    content = [line.rstrip() for line in text.strip().splitlines() if line.strip()]
    doc.sections[section] = content or [PLACEHOLDER]


def append_section_bullets(doc: MarkdownDoc, section: str, values: Iterable[str]) -> None:
    doc.sections[section] = append_unique_bullets(doc.sections.get(section, [PLACEHOLDER]), values)


def append_structured_values(doc: MarkdownDoc, section: str, pairs: Iterable[tuple[str, str]]) -> None:
    current = clear_placeholder(doc.sections.get(section, [PLACEHOLDER]))
    for first, second in pairs:
        head = first.strip()
        tail = second.strip()
        if not head:
            continue
        bullet = f"- `{head}` - {tail}" if tail else f"- `{head}`"
        if bullet not in current:
            current.append(bullet)
    doc.sections[section] = current or [PLACEHOLDER]


def parse_task_items(lines: Iterable[str]) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for line in lines:
        match = TASK_PATTERN.match(line.strip())
        if not match:
            continue
        tasks.append({"status": match.group(1), "text": match.group(2).strip()})
    return tasks


def render_task_items(tasks: Iterable[dict[str, str]]) -> list[str]:
    rendered = [f"- [{task['status']}] {task['text']}" for task in tasks if task.get("text")]
    return rendered or [PLACEHOLDER]


def upsert_task(doc: MarkdownDoc, text: str, status: str | None = None) -> None:
    task_text = text.strip()
    if not task_text:
        return
    normalized_status = (status or " ").strip() or " "
    tasks = parse_task_items(clear_placeholder(doc.sections.get("Tasks", [PLACEHOLDER])))
    for task in tasks:
        if task["text"] == task_text:
            if status is not None:
                task["status"] = normalized_status
            doc.sections["Tasks"] = render_task_items(tasks)
            return
    tasks.append({"status": normalized_status, "text": task_text})
    doc.sections["Tasks"] = render_task_items(tasks)


def set_task_status(doc: MarkdownDoc, text: str, status: str) -> bool:
    task_text = text.strip()
    tasks = parse_task_items(clear_placeholder(doc.sections.get("Tasks", [PLACEHOLDER])))
    updated = False
    for task in tasks:
        if task["text"] == task_text:
            task["status"] = status.strip() or " "
            updated = True
            break
    doc.sections["Tasks"] = render_task_items(tasks)
    return updated


def parse_workstream_entries(lines: Iterable[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in lines:
        match = WORKSTREAM_PATTERN.match(line.strip())
        if not match:
            continue
        entries.append(match.groupdict())
    return entries


def parse_status_entries(lines: Iterable[str]) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for line in lines:
        match = STATUS_PATTERN.match(line.strip())
        if not match:
            continue
        entries.append(match.groupdict())
    return entries


def render_workstream_entries(entries: Iterable[dict[str, str]]) -> list[str]:
    rendered = [
        (
            f"- `{entry['slug']}` | status: {entry['status']} | owner: {entry['owner']} "
            f"| file: `{entry['file']}` | objective: {entry['objective']}"
        )
        for entry in entries
    ]
    return rendered or [WORKSTREAM_PLACEHOLDER]


def render_status_entries(entries: Iterable[dict[str, str]]) -> list[str]:
    rendered = [
        (
            f"- `{entry['slug']}` | status: {entry['status']} | execution: {entry['execution']} "
            f"| owner: {entry['owner']} | file: `{entry['file']}` | next: {entry['next']}"
        )
        for entry in entries
    ]
    return rendered or [STATUS_PLACEHOLDER]


def upsert_workstream_entry(
    doc: MarkdownDoc,
    slug: str,
    objective: str,
    status: str = "planned",
    owner: str = "unassigned",
) -> None:
    entries = parse_workstream_entries(clear_placeholder(doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    target_file = f"todos/{slug}.md"
    for entry in entries:
        if entry["slug"] == slug:
            entry["status"] = status
            entry["owner"] = owner
            entry["objective"] = objective
            entry["file"] = target_file
            doc.sections["Workstreams"] = render_workstream_entries(entries)
            return
    entries.append(
        {
            "slug": slug,
            "status": status,
            "owner": owner,
            "file": target_file,
            "objective": objective,
        }
    )
    doc.sections["Workstreams"] = render_workstream_entries(entries)


def remove_workstream_entry(doc: MarkdownDoc, slug: str) -> None:
    entries = parse_workstream_entries(clear_placeholder(doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    filtered = [entry for entry in entries if entry["slug"] != slug]
    doc.sections["Workstreams"] = render_workstream_entries(filtered)


def is_done_status(status: str) -> bool:
    return status.strip() in DONE_STATUSES


def derive_execution_state(status: str, current: str | None = None) -> str:
    existing = (current or "").strip()
    if existing:
        return existing
    normalized = status.strip()
    if normalized == "planned":
        return "ready"
    if normalized == "in_progress":
        return "claimed"
    if normalized == "blocked":
        return "idle"
    if normalized in DONE_STATUSES:
        return "closed"
    return "idle"


def first_status_next_action(next_action: str | None = None, doc: MarkdownDoc | None = None) -> str:
    if next_action and next_action.strip():
        return next_action.strip()
    if doc is not None:
        lines = clear_placeholder(doc.sections.get("Next Actions", [PLACEHOLDER]))
        if lines:
            return re.sub(r"^- ", "", lines[0]).strip()
    return "Review the workstream ledger and pick the next concrete step."


def upsert_status_entry(
    doc: MarkdownDoc,
    slug: str,
    objective: str,
    status: str,
    owner: str,
    execution: str | None = None,
    next_action: str | None = None,
) -> None:
    entries = parse_status_entries(clear_placeholder(doc.sections.get("Workstreams", [STATUS_PLACEHOLDER])))
    target_file = f"todos/{slug}.md"
    normalized_execution = derive_execution_state(status, execution)
    summary = next_action.strip() if next_action and next_action.strip() else objective.strip() or humanize_slug(slug)
    for entry in entries:
        if entry["slug"] == slug:
            entry["status"] = status
            entry["execution"] = normalized_execution
            entry["owner"] = owner
            entry["file"] = target_file
            entry["next"] = summary
            doc.sections["Workstreams"] = render_status_entries(entries)
            refresh_cleanup_status(doc)
            return
    entries.append(
        {
            "slug": slug,
            "status": status,
            "execution": normalized_execution,
            "owner": owner,
            "file": target_file,
            "next": summary,
        }
    )
    doc.sections["Workstreams"] = render_status_entries(entries)
    refresh_cleanup_status(doc)


def sync_status_entries_from_root(root_doc: MarkdownDoc, status_doc: MarkdownDoc) -> None:
    root_entries = parse_workstream_entries(clear_placeholder(root_doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    current_entries = {
        entry["slug"]: entry
        for entry in parse_status_entries(clear_placeholder(status_doc.sections.get("Workstreams", [STATUS_PLACEHOLDER])))
    }
    synced: list[dict[str, str]] = []
    for entry in root_entries:
        current = current_entries.get(entry["slug"], {})
        synced.append(
            {
                "slug": entry["slug"],
                "status": entry["status"],
                "execution": derive_execution_state(entry["status"], current.get("execution")),
                "owner": entry["owner"],
                "file": entry["file"],
                "next": current.get("next", entry["objective"]),
            }
        )
    status_doc.sections["Workstreams"] = render_status_entries(synced)
    refresh_cleanup_status(status_doc)


def remove_status_entry(doc: MarkdownDoc, slug: str) -> None:
    entries = parse_status_entries(clear_placeholder(doc.sections.get("Workstreams", [STATUS_PLACEHOLDER])))
    filtered = [entry for entry in entries if entry["slug"] != slug]
    doc.sections["Workstreams"] = render_status_entries(filtered)
    refresh_cleanup_status(doc)


def refresh_cleanup_status(doc: MarkdownDoc) -> None:
    entries = parse_status_entries(clear_placeholder(doc.sections.get("Workstreams", [STATUS_PLACEHOLDER])))
    unfinished = [entry["slug"] for entry in entries if not is_done_status(entry["status"])]
    if unfinished:
        doc.sections["Cleanup Status"] = [
            "- Cleanup mode is explicit only.",
            f"- Safe to call `todo-cleanup`: no, waiting on {', '.join(unfinished)}.",
        ]
        return
    if entries:
        doc.sections["Cleanup Status"] = [
            "- Cleanup mode is explicit only.",
            "- Safe to call `todo-cleanup`: yes, every tracked workstream is done.",
        ]
        return
    doc.sections["Cleanup Status"] = [
        "- Cleanup mode is explicit only.",
        "- Safe to call `todo-cleanup`: yes, there are no tracked workstreams left.",
    ]


def pickup_ready_entries(entries: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    ready: list[dict[str, str]] = []
    for entry in entries:
        if is_done_status(entry["status"]) or entry["status"] == "blocked":
            continue
        if entry.get("execution", "").strip() not in PICKUP_READY_STATES:
            continue
        ready.append(entry)
    return ready


def ensure_root_files(repo_root: Path) -> None:
    root_doc = load_root_doc(repo_root)
    write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)
    (repo_root / "todos").mkdir(parents=True, exist_ok=True)
    status_doc = load_status_doc(repo_root)
    sync_status_entries_from_root(root_doc, status_doc)
    write_document(repo_root / "todo-status.md", status_doc, STATUS_SECTION_ORDER)


def ensure_workstream_file(
    repo_root: Path,
    slug: str,
    objective: str,
    status: str,
    owner: str,
    execution: str | None = None,
    next_action: str | None = None,
) -> Path:
    ensure_root_files(repo_root)
    workstream_doc = load_workstream_doc(repo_root, slug, objective)
    if objective and workstream_doc.sections.get("Summary") in ([PLACEHOLDER], []):
        workstream_doc.sections["Summary"] = [objective]
    workstream_path = repo_root / "todos" / f"{slug}.md"
    write_document(workstream_path, workstream_doc, WORKSTREAM_SECTION_ORDER)

    root_doc = load_root_doc(repo_root)
    upsert_workstream_entry(root_doc, slug, objective or humanize_slug(slug), status=status, owner=owner)
    write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)

    status_doc = load_status_doc(repo_root)
    sync_status_entries_from_root(root_doc, status_doc)
    upsert_status_entry(
        status_doc,
        slug=slug,
        objective=objective or humanize_slug(slug),
        status=status,
        owner=owner,
        execution=execution,
        next_action=first_status_next_action(next_action, workstream_doc),
    )
    write_document(repo_root / "todo-status.md", status_doc, STATUS_SECTION_ORDER)
    return workstream_path


def managed_agents_block() -> str:
    return "\n".join(
        [
            AGENTS_START,
            "## Workflow Ledger",
            "",
            "- For substantial multi-step work, consult `todos.md` first.",
            "- Consult `todo-status.md` for pickup-ready, claimed, and idle workstreams before starting parallel work.",
            "- Treat `todos.md` as the canonical active plan and progress ledger.",
            "- For concurrent workstreams, consult the relevant file under `todos/`.",
            "- In plan mode, consult `todo-orchestrator/references/planning-workflow.md`.",
            "- In implementation mode, continue from the recorded plan non-interactively unless truly blocked.",
            "- Prefer relevant repo-local skills and reference files when they match the task.",
            AGENTS_END,
            "",
        ]
    )


def ensure_agents_md(repo_root: Path) -> Path:
    path = repo_root / "AGENTS.md"
    block = managed_agents_block()
    if path.exists():
        text = path.read_text(encoding="utf-8")
        pattern = re.compile(
            rf"{re.escape(AGENTS_START)}.*?{re.escape(AGENTS_END)}\n?",
            re.DOTALL,
        )
        if pattern.search(text):
            text = pattern.sub(block, text).rstrip() + "\n"
        else:
            text = text.rstrip() + "\n\n" + block
    else:
        text = "# Repo Guidance\n\n" + block
    path.write_text(text, encoding="utf-8")
    return path


def detect_resume_state(repo_root: Path) -> dict[str, object]:
    root_path = repo_root / "todos.md"
    if not root_path.exists():
        return {
            "has_root_todos": False,
            "has_agents_md": (repo_root / "AGENTS.md").exists(),
            "active_workstreams": [],
            "pickup_ready_workstreams": [],
            "claimed_workstreams": [],
            "cleanup_ready": False,
        }
    root_doc = load_root_doc(repo_root)
    entries = parse_workstream_entries(clear_placeholder(root_doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    active = [entry for entry in entries if not is_done_status(entry["status"])]
    status_doc = load_status_doc(repo_root)
    status_entries = parse_status_entries(clear_placeholder(status_doc.sections.get("Workstreams", [STATUS_PLACEHOLDER])))
    claimed = [entry for entry in status_entries if entry.get("execution", "").strip() == "claimed"]
    return {
        "has_root_todos": True,
        "has_agents_md": (repo_root / "AGENTS.md").exists(),
        "active_workstreams": active,
        "pickup_ready_workstreams": pickup_ready_entries(status_entries),
        "claimed_workstreams": claimed,
        "cleanup_ready": bool(status_entries) and not active,
    }


def parse_frontmatter(text: str) -> dict[str, str]:
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        return {}
    data: dict[str, str] = {}
    current_key: str | None = None
    block_key: str | None = None
    block_lines: list[str] = []
    for raw_line in match.group(1).splitlines():
        if re.match(r"^[A-Za-z0-9_-]+:", raw_line):
            if block_key is not None:
                data[block_key] = " ".join(block_lines).strip()
                block_key = None
                block_lines = []
            current_key = None
            key, value = raw_line.split(":", 1)
            cleaned_key = key.strip()
            cleaned_value = value.strip()
            if cleaned_value in {">", ">-", "|", "|-"}:
                current_key = cleaned_key
                block_key = cleaned_key
                data.setdefault(cleaned_key, "")
            else:
                data[cleaned_key] = cleaned_value.strip('"')
                current_key = cleaned_key
            continue
        if raw_line.startswith((" ", "\t")) and current_key is not None:
            continuation = raw_line.strip()
            if block_key == current_key:
                if continuation:
                    block_lines.append(continuation)
            elif continuation:
                data[current_key] = f"{data.get(current_key, '')} {continuation}".strip()
            continue
        if block_key is not None:
            data[block_key] = " ".join(block_lines).strip()
            block_key = None
            block_lines = []
        current_key = None
    if block_key is not None:
        data[block_key] = " ".join(block_lines).strip()
    return data


def dumps_json(data: object, pretty: bool = False) -> str:
    if pretty:
        return json.dumps(data, indent=2, sort_keys=True) + "\n"
    return json.dumps(data, separators=(",", ":"), sort_keys=True) + "\n"
