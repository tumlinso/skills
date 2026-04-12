#!/usr/bin/env python3
"""Detect manuscript context and likely figure locations in a Quarto manuscript repo."""

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
AUX_DIR_MARKERS = {"notes", "presentation", "presentations", "slides", "poster"}
SECTION_DIR_MARKERS = {"sections", "chapters", "appendix", "appendices"}
MANUSCRIPT_NAME_HINTS = {"main", "index", "manuscript", "paper", "article"}
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
FIGURE_ROOT_CHOICES = (
    Path("figures"),
    Path("figs"),
    Path("plots"),
    Path("assets") / "figures",
)
DATA_KEYWORDS = {
    "umap",
    "embedding",
    "heatmap",
    "volcano",
    "marker",
    "expression",
    "qc",
    "pseudotime",
    "barplot",
    "violin",
    "scatter",
    "plot",
}
SCHEMATIC_KEYWORDS = {
    "workflow",
    "diagram",
    "schematic",
    "overview",
    "pipeline",
    "study design",
    "conceptual",
    "model summary",
    "cartoon",
}
DATA_EXTENSIONS = {".csv", ".tsv", ".tab", ".txt", ".mtx", ".h5ad", ".loom", ".parquet"}


def rel_path(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def extract_front_matter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text
    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def clean_scalar(value: str) -> str:
    text = value.strip().rstrip(",")
    if text and text[0] in {'"', "'"} and text[-1] == text[0]:
        return text[1:-1]
    return text


def parse_value_list(value: str) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        return [clean_scalar(item) for item in value[1:-1].split(",") if clean_scalar(item)]
    return [clean_scalar(value)]


def parse_front_matter(front_matter: str | None) -> dict[str, object]:
    data: dict[str, object] = {"title": None, "author": None, "format_hints": [], "paths": {}}
    if not front_matter:
        return data

    lines = front_matter.splitlines()
    paths: dict[str, list[str]] = {}
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)([A-Za-z0-9_-]+)\s*:\s*(.*)$", line)
        if not match:
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
                lookahead += 1
            paths[key] = [item for item in collected if item]
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


def is_render_like(path: Path) -> bool:
    return any(part in RENDER_DIR_NAMES for part in path.parts)


def is_auxiliary(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    stem = path.stem.lower()
    return bool(parts & AUX_DIR_MARKERS) or stem in {"references", "presentation"}


def is_section(path: Path) -> bool:
    parts = {part.lower() for part in path.parts}
    return bool(parts & SECTION_DIR_MARKERS) or path.name.startswith("_")


def score_qmd(path: Path, root: Path, parsed: dict[str, object], headings: list[str], body: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    stem = path.stem.lower()
    rel = path.relative_to(root)

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
        reasons.append("references support files")
    if stem in MANUSCRIPT_NAME_HINTS:
        score += 3
        reasons.append("manuscript-like filename")
    if body.count("\n") > 12:
        score += 1
        reasons.append("substantial body")
    if any(heading.lower() in MANUSCRIPT_HEADING_HINTS for heading in headings):
        score += 2
        reasons.append("contains manuscript headings")
    if is_section(rel):
        score -= 4
        reasons.append("looks like subsection file")
    if is_auxiliary(rel):
        score -= 5
        reasons.append("looks auxiliary")
    if is_render_like(rel):
        score -= 6
        reasons.append("inside render path")
    if rel.parts and rel.parts[0] == "docs":
        score -= 2
        reasons.append("inside docs requires proof of source role")
    return score, reasons


def detect_output_dir(quarto_config: Path | None) -> str | None:
    if not quarto_config or not quarto_config.exists():
        return None
    text = read_text(quarto_config)
    match = re.search(r"^\s*output-dir:\s*['\"]?([^'\"]+)['\"]?\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def classify_docs_role(root: Path, output_dir: str | None) -> dict[str, object]:
    docs_dir = root / "docs"
    if not docs_dir.exists():
        return {"status": "absent"}
    if output_dir == "docs":
        return {"status": "output", "reason": "_quarto.yml points output-dir at docs"}
    html_files = list(docs_dir.rglob("*.html"))
    qmd_files = list(docs_dir.rglob("*.qmd"))
    if html_files and not qmd_files:
        return {"status": "output", "reason": "docs mostly contains rendered html"}
    if qmd_files and not html_files:
        return {"status": "source", "reason": "docs contains only qmd source candidates"}
    return {"status": "ambiguous"}


def choose_existing_figure_root(root: Path) -> Path | None:
    best_path = None
    best_score = -1
    for candidate in FIGURE_ROOT_CHOICES:
        path = root / candidate
        if not path.exists() or not path.is_dir():
            continue
        score = 1
        for subdir in ("generated/data", "generated/schematics", "scripts", "specs", "captions"):
            if (path / subdir).exists():
                score += 2
        score += len(list(path.glob("*.svg")))
        score += len(list(path.glob("*.png")))
        if score > best_score:
            best_score = score
            best_path = path
    return best_path


def choose_path(root_dir: Path, candidates: list[str], fallback: str) -> str:
    for candidate in candidates:
        if (root_dir / candidate).exists():
            return str((root_dir.relative_to(root_dir.parent) / candidate) if root_dir.parent != root_dir else Path(candidate))
    return str(root_dir.relative_to(root_dir.parent) / fallback) if root_dir.parent != root_dir else fallback


def build_layout(root: Path, figure_root: Path | None) -> dict[str, object]:
    if figure_root is None:
        root_rel = "figures"
        return {
            "status": "proposed",
            "root_dir": root_rel,
            "data_dir": "figures/generated/data",
            "schematic_dir": "figures/generated/schematics",
            "data_script_dir": "figures/scripts/data",
            "schematic_script_dir": "figures/scripts/schematics",
            "specs_dir": "figures/specs",
            "captions_dir": "figures/captions",
        }

    root_rel = rel_path(figure_root, root)
    return {
        "status": "existing",
        "root_dir": root_rel,
        "data_dir": str(Path(root_rel) / resolve_generated_subdir(figure_root, "data")),
        "schematic_dir": str(Path(root_rel) / resolve_generated_subdir(figure_root, "schematics")),
        "data_script_dir": str(Path(root_rel) / resolve_script_subdir(figure_root, "data")),
        "schematic_script_dir": str(Path(root_rel) / resolve_script_subdir(figure_root, "schematics")),
        "specs_dir": str(Path(root_rel) / next_existing_dir(figure_root, ["specs", "metadata"], "specs")),
        "captions_dir": str(Path(root_rel) / next_existing_dir(figure_root, ["captions"], "captions")),
    }


def next_existing_dir(root_dir: Path, candidates: list[str], fallback: str) -> str:
    for candidate in candidates:
        if (root_dir / candidate).exists():
            return candidate
    return fallback


def resolve_generated_subdir(root_dir: Path, mode: str) -> str:
    if (root_dir / f"generated/{mode}").exists():
        return f"generated/{mode}"
    sibling = "schematics" if mode == "data" else "data"
    if (root_dir / f"generated/{sibling}").exists() or (root_dir / "generated").exists():
        return f"generated/{mode}"
    if (root_dir / mode).exists():
        return mode
    return f"generated/{mode}"


def resolve_script_subdir(root_dir: Path, mode: str) -> str:
    if (root_dir / f"scripts/{mode}").exists():
        return f"scripts/{mode}"
    sibling = "schematics" if mode == "data" else "data"
    if (root_dir / f"scripts/{sibling}").exists() or (root_dir / "scripts").exists():
        return f"scripts/{mode}"
    return f"scripts/{mode}"


def infer_figure_mode(description: str | None, input_paths: list[str] | None) -> tuple[str, str]:
    if input_paths:
        return "data-figure", "repo-local figure inputs were provided"

    text = (description or "").lower()
    if any(keyword in text for keyword in SCHEMATIC_KEYWORDS):
        return "schematic-figure", "description uses schematic or workflow language"
    if any(keyword in text for keyword in DATA_KEYWORDS):
        return "data-figure", "description uses data-figure terminology"
    return "schematic-figure", "no explicit data input was provided"


def analyze_repo(path_input: Path, description: str | None = None, input_paths: list[str] | None = None) -> dict[str, object]:
    path = path_input.resolve()
    root = path if path.is_dir() else path.parent
    quarto_config = root / "_quarto.yml"
    output_dir = detect_output_dir(quarto_config if quarto_config.exists() else None)

    qmd_files = sorted(root.rglob("*.qmd")) if path.is_dir() else [path]
    candidates = []
    section_files = []
    for qmd_path in qmd_files:
        if is_render_like(qmd_path.relative_to(root)):
            continue
        text = read_text(qmd_path)
        front_matter, body = extract_front_matter(text)
        parsed = parse_front_matter(front_matter)
        headings = extract_headings(body)
        score, reasons = score_qmd(qmd_path, root, parsed, headings, body)
        rel = rel_path(qmd_path, root)
        entry = {"path": rel, "score": score, "reasons": reasons}
        candidates.append(entry)
        if is_section(qmd_path.relative_to(root)):
            section_files.append(rel)
    candidates.sort(key=lambda item: (-item["score"], item["path"]))

    primary = candidates[0]["path"] if candidates else None
    manuscript_files = []
    if primary:
        manuscript_files.append(primary)
    manuscript_files.extend(path for path in section_files if path not in manuscript_files)

    figure_root = choose_existing_figure_root(root)
    figure_layout = build_layout(root, figure_root)
    suggested_mode, rationale = infer_figure_mode(description, input_paths)
    return {
        "input_path": str(path_input),
        "root": str(root),
        "quarto_config": "_quarto.yml" if quarto_config.exists() else None,
        "primary_manuscript": primary,
        "manuscript_files": manuscript_files,
        "candidate_manuscripts": candidates,
        "section_files": sorted(section_files),
        "docs_role": classify_docs_role(root, output_dir),
        "figure_layout": figure_layout,
        "suggested_mode": suggested_mode,
        "suggested_mode_reason": rationale,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Quarto manuscript file or directory")
    parser.add_argument("--description", help="Optional figure description to help infer the mode")
    parser.add_argument("--input", action="append", default=[], help="Optional repo-local input path to help infer the mode")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    result = analyze_repo(Path(args.path), description=args.description, input_paths=args.input or None)
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
