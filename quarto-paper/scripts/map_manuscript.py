#!/usr/bin/env python3
"""Map the likely source structure of a Quarto manuscript project."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

RENDER_DIR_NAMES = {
    "_site",
    "site_libs",
    "_freeze",
    "_book",
    "_manuscript",
    ".quarto",
    "__pycache__",
}
RENDER_FILE_SUFFIXES = {".html", ".pdf", ".epub"}
AUX_DIR_MARKERS = {"notes", "presentation", "presentations", "slides", "poster"}
SECTION_DIR_MARKERS = {"sections", "chapters", "appendix", "appendices"}
MANUSCRIPT_NAME_HINTS = {"main", "index", "manuscript", "paper", "article"}
MANUSCRIPT_STEM_PREFIXES = ("preprint",)
MANUSCRIPT_HEADING_HINTS = {
    "abstract",
    "introduction",
    "background",
    "methods",
    "results",
    "discussion",
    "conclusion",
    "references",
}
INCLUDE_KEYS = {
    "bibliography",
    "csl",
    "include-in-header",
    "include-before-body",
    "include-after-body",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def rel_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def extract_front_matter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text

    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            front_matter = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return front_matter, body
    return None, text


def clean_scalar(value: str) -> str:
    value = value.strip().rstrip(",")
    if not value:
        return value
    if value[0] in {"'", '"'} and value[-1] == value[0]:
        return value[1:-1]
    return value


def parse_value_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        return [clean_scalar(part) for part in value[1:-1].split(",") if clean_scalar(part)]
    return [clean_scalar(value)]


def parse_front_matter(front_matter: str | None) -> dict[str, object]:
    data: dict[str, object] = {
        "title": None,
        "author": None,
        "format_hints": [],
        "paths": {},
    }
    if not front_matter:
        return data

    lines = front_matter.splitlines()
    index = 0
    paths: dict[str, list[str]] = {}
    while index < len(lines):
        line = lines[index]
        match = re.match(r"^(\s*)([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not match:
            index += 1
            continue

        indent = len(match.group(1))
        key = match.group(2)
        value = match.group(3).strip()

        if key in {"title", "author"} and value:
            data[key] = clean_scalar(value)
        if key == "format" and value:
            data["format_hints"] = parse_value_list(value)
        elif key in {"pdf", "html", "docx", "typst", "manuscript", "article"}:
            data.setdefault("format_hints", []).append(key)

        if key in INCLUDE_KEYS:
            collected = parse_value_list(value)
            lookahead = index + 1
            while lookahead < len(lines):
                next_line = lines[lookahead]
                if not next_line.strip():
                    lookahead += 1
                    continue
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= indent:
                    break
                item_match = re.match(r"^\s*-\s+(.*)$", next_line)
                if item_match:
                    collected.extend(parse_value_list(item_match.group(1)))
                elif ":" not in next_line.strip():
                    collected.append(clean_scalar(next_line.strip()))
                lookahead += 1
            paths[key] = [item for item in collected if item]

        index += 1

    data["format_hints"] = sorted(set(data["format_hints"]))  # type: ignore[assignment]
    data["paths"] = paths
    return data


def extract_headings(body: str) -> list[str]:
    headings = []
    for line in body.splitlines():
        match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
    return headings


def is_render_like_path(path: Path) -> bool:
    return any(part in RENDER_DIR_NAMES for part in path.parts)


def is_auxiliary_path(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    stem = path.stem.lower()
    return bool(parts & AUX_DIR_MARKERS) or stem in {"references", "presentation"} or any(
        marker in stem for marker in ("notes", "presentation", "slides")
    )


def is_section_path(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & SECTION_DIR_MARKERS) or path.name.startswith("_")


def score_qmd(path: Path, root: Path, parsed: dict[str, object], headings: list[str], body: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    stem = path.stem.lower()
    parent = path.parent

    if path.parent == root:
        score += 3
        reasons.append("root-level qmd")

    if parsed.get("title"):
        score += 2
        reasons.append("has title front matter")
    if parsed.get("author"):
        score += 1
        reasons.append("has author front matter")
    if parsed.get("format_hints"):
        score += 2
        reasons.append("declares format")
    if any(parsed.get("paths", {}).get(key) for key in ("bibliography", "csl", "include-in-header")):
        score += 2
        reasons.append("references bibliography or csl or include files")

    if stem in MANUSCRIPT_NAME_HINTS or stem.startswith(MANUSCRIPT_STEM_PREFIXES):
        score += 3
        reasons.append("manuscript-like filename")

    if body.count("\n") > 20:
        score += 1
        reasons.append("substantial manuscript body")
    if any(heading.lower() in MANUSCRIPT_HEADING_HINTS for heading in headings):
        score += 2
        reasons.append("contains manuscript headings")

    if is_section_path(path.relative_to(root)):
        score -= 4
        reasons.append("looks like subsection file")
    if is_auxiliary_path(path.relative_to(root)):
        score -= 5
        reasons.append("looks like notes or presentation material")
    if is_render_like_path(path.relative_to(root)):
        score -= 6
        reasons.append("inside render-like path")
    if stem == "references":
        score -= 3
        reasons.append("references stub, not main manuscript")
    if parent.name.lower() == "docs":
        score -= 2
        reasons.append("inside docs requires explicit proof of source role")

    return score, reasons


def detect_output_dir(quarto_config: Path | None) -> str | None:
    if not quarto_config or not quarto_config.exists():
        return None
    text = read_text(quarto_config)
    match = re.search(r"^\s*output-dir:\s*['\"]?([^'\"]+)['\"]?\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def detect_project_type(quarto_config: Path | None) -> str | None:
    if not quarto_config or not quarto_config.exists():
        return None
    text = read_text(quarto_config)
    match = re.search(r"^\s*type:\s*['\"]?([^'\"]+)['\"]?\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def resolve_support_files(
    root: Path, qmd_path: Path, raw_paths: list[str], seen: set[tuple[str, str]], bucket: list[dict[str, object]]
) -> None:
    for raw_path in raw_paths:
        if raw_path.startswith("http://") or raw_path.startswith("https://"):
            key = ("remote", raw_path)
            if key in seen:
                continue
            seen.add(key)
            bucket.append({"path": raw_path, "exists": False, "source": rel_path(qmd_path, root)})
            continue

        resolved = (qmd_path.parent / raw_path).resolve()
        try:
            rel = str(resolved.relative_to(root.resolve()))
        except ValueError:
            rel = raw_path
        key = ("local", rel)
        if key in seen:
            continue
        seen.add(key)
        bucket.append({"path": rel, "exists": resolved.exists(), "source": rel_path(qmd_path, root)})


def classify_docs(root: Path, primary_manuscript: str | None, quarto_config: Path | None) -> dict[str, str]:
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return {"status": "absent", "reason": "docs/ does not exist"}

    output_dir = detect_output_dir(quarto_config)
    if output_dir == "docs":
        return {"status": "output", "reason": "_quarto.yml sets output-dir to docs"}

    docs_qmd = sorted(docs_dir.rglob("*.qmd"))
    docs_rendered = [
        path
        for path in docs_dir.rglob("*")
        if path.is_file() and (path.suffix.lower() in RENDER_FILE_SUFFIXES or "site_libs" in path.parts)
    ]

    if primary_manuscript and primary_manuscript.startswith("docs/"):
        return {"status": "source", "reason": "primary manuscript is inside docs"}
    if docs_rendered and not docs_qmd:
        return {"status": "output", "reason": "docs contains rendered artifacts and no qmd source"}
    if docs_qmd and any((root / primary_manuscript).exists() for primary_manuscript in [primary_manuscript] if primary_manuscript):
        return {"status": "ambiguous", "reason": "docs contains qmd files but primary manuscript lives outside docs"}
    if docs_qmd:
        return {"status": "source", "reason": "docs contains the only visible qmd sources"}
    return {"status": "ambiguous", "reason": "docs exists without enough evidence to classify safely"}


def analyze(root_input: Path) -> dict[str, object]:
    path = root_input.resolve()
    root = path.parent if path.is_file() else path
    quarto_config = root / "_quarto.yml"

    qmd_files = sorted(root.rglob("*.qmd"))
    candidate_manuscripts = []
    section_files = []
    auxiliary_qmd_files = []
    bibliography_files: list[dict[str, object]] = []
    csl_files: list[dict[str, object]] = []
    include_files: list[dict[str, object]] = []
    support_seen: set[tuple[str, str]] = set()
    render_like_paths = []

    for render_name in sorted(RENDER_DIR_NAMES | {"docs"}):
        render_dir = root / render_name
        if render_dir.exists():
            render_like_paths.append(str(render_dir.relative_to(root)))

    for bib_path in sorted(root.rglob("*.bib")):
        if any(part in RENDER_DIR_NAMES for part in bib_path.parts):
            continue
        support_seen.add(("local", rel_path(bib_path, root)))
        bibliography_files.append({"path": rel_path(bib_path, root), "exists": True, "source": None})

    for csl_path in sorted(root.rglob("*.csl")):
        if any(part in RENDER_DIR_NAMES for part in csl_path.parts):
            continue
        support_seen.add(("local", rel_path(csl_path, root)))
        csl_files.append({"path": rel_path(csl_path, root), "exists": True, "source": None})

    for qmd_path in qmd_files:
        text = read_text(qmd_path)
        front_matter, body = extract_front_matter(text)
        parsed = parse_front_matter(front_matter)
        headings = extract_headings(body)
        rel = rel_path(qmd_path, root)
        score, reasons = score_qmd(qmd_path, root, parsed, headings, body)

        for key, bucket in (
            ("bibliography", bibliography_files),
            ("csl", csl_files),
            ("include-in-header", include_files),
            ("include-before-body", include_files),
            ("include-after-body", include_files),
        ):
            raw_paths = parsed.get("paths", {}).get(key, [])
            if raw_paths:
                resolve_support_files(root, qmd_path, raw_paths, support_seen, bucket)

        record = {
            "path": rel,
            "score": score,
            "title": parsed.get("title"),
            "headings": headings[:8],
            "reasons": reasons,
        }
        candidate_manuscripts.append(record)

        rel_path_obj = qmd_path.relative_to(root)
        if is_section_path(rel_path_obj) and not is_auxiliary_path(rel_path_obj):
            section_files.append(rel)
        if is_auxiliary_path(rel_path_obj):
            auxiliary_qmd_files.append(rel)

    candidate_manuscripts.sort(key=lambda item: (-int(item["score"]), str(item["path"])))

    primary = None
    for candidate in candidate_manuscripts:
        if int(candidate["score"]) <= 0:
            continue
        rel = Path(str(candidate["path"]))
        if is_auxiliary_path(rel) or is_section_path(rel):
            continue
        primary = str(candidate["path"])
        break

    docs_role = classify_docs(root, primary, quarto_config if quarto_config.exists() else None)

    return {
        "input_path": str(root_input),
        "root": str(root),
        "quarto_config": "_quarto.yml" if quarto_config.exists() else None,
        "project_type": detect_project_type(quarto_config if quarto_config.exists() else None),
        "output_dir": detect_output_dir(quarto_config if quarto_config.exists() else None),
        "primary_manuscript": primary,
        "candidate_manuscripts": candidate_manuscripts,
        "section_files": sorted(section_files),
        "auxiliary_qmd_files": sorted(auxiliary_qmd_files),
        "bibliography_files": bibliography_files,
        "csl_files": csl_files,
        "include_files": include_files,
        "render_like_paths": sorted(render_like_paths),
        "docs_role": docs_role,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Quarto repository or manuscript directory")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    result = analyze(Path(args.path))
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
