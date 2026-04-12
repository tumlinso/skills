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

PLACEHOLDER = "_None recorded yet._"
WORKSTREAM_PLACEHOLDER = "_No active workstreams yet._"
TASK_PATTERN = re.compile(r"^- \[([ x~!])\] (.+)$")
WORKSTREAM_PATTERN = re.compile(
    r"^- `(?P<slug>[^`]+)` \| status: (?P<status>[^|]+) \| owner: (?P<owner>[^|]+) "
    r"\| file: `(?P<file>[^`]+)` \| objective: (?P<objective>.+)$"
)
FRONTMATTER_PATTERN = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
AGENTS_START = "<!-- todo-orchestrator:start -->"
AGENTS_END = "<!-- todo-orchestrator:end -->"


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


def clear_placeholder(lines: list[str], placeholder: str = PLACEHOLDER) -> list[str]:
    normalized = normalize_text_lines(lines)
    if normalized == [placeholder] or normalized == [WORKSTREAM_PLACEHOLDER]:
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


def render_workstream_entries(entries: Iterable[dict[str, str]]) -> list[str]:
    rendered = [
        (
            f"- `{entry['slug']}` | status: {entry['status']} | owner: {entry['owner']} "
            f"| file: `{entry['file']}` | objective: {entry['objective']}"
        )
        for entry in entries
    ]
    return rendered or [WORKSTREAM_PLACEHOLDER]


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


def ensure_root_files(repo_root: Path) -> None:
    root_doc = load_root_doc(repo_root)
    write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)
    (repo_root / "todos").mkdir(parents=True, exist_ok=True)


def ensure_workstream_file(repo_root: Path, slug: str, objective: str, status: str, owner: str) -> Path:
    ensure_root_files(repo_root)
    workstream_doc = load_workstream_doc(repo_root, slug, objective)
    if objective and workstream_doc.sections.get("Summary") in ([PLACEHOLDER], []):
        workstream_doc.sections["Summary"] = [objective]
    workstream_path = repo_root / "todos" / f"{slug}.md"
    write_document(workstream_path, workstream_doc, WORKSTREAM_SECTION_ORDER)

    root_doc = load_root_doc(repo_root)
    upsert_workstream_entry(root_doc, slug, objective or humanize_slug(slug), status=status, owner=owner)
    write_document(repo_root / "todos.md", root_doc, ROOT_SECTION_ORDER)
    return workstream_path


def managed_agents_block() -> str:
    return "\n".join(
        [
            AGENTS_START,
            "## Workflow Ledger",
            "",
            "- For substantial multi-step work, consult `todos.md` first.",
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
        }
    root_doc = load_root_doc(repo_root)
    entries = parse_workstream_entries(clear_placeholder(root_doc.sections.get("Workstreams", [WORKSTREAM_PLACEHOLDER])))
    active = [entry for entry in entries if entry["status"] not in {"done", "complete", "archived"}]
    return {
        "has_root_todos": True,
        "has_agents_md": (repo_root / "AGENTS.md").exists(),
        "active_workstreams": active,
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
