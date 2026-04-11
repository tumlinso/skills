#!/usr/bin/env python3
"""Extract likely citation gaps from Quarto manuscript prose."""

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
HEURISTICS = [
    (
        "quantitative claim",
        re.compile(
            r"\b\d+(?:\.\d+)?(?:\s*%|\s+percent|\s+fold|\s+x|\s+times|\s+million|\s+billion|\s+thousand)\b",
            re.IGNORECASE,
        ),
        "quantitative or benchmark source",
    ),
    (
        "time or prevalence claim",
        re.compile(r"\b(?:19|20)\d{2}\b|\b(?:prevalence|incidence|mortality|survival)\b", re.IGNORECASE),
        "epidemiology or historical source",
    ),
    (
        "consensus framing",
        re.compile(
            r"\b(?:widely|commonly|often|generally|well known|established|classical|canonical|standard)\b",
            re.IGNORECASE,
        ),
        "review or consensus source",
    ),
    (
        "evidence attribution",
        re.compile(
            r"\b(?:studies|evidence|shown|demonstrated|reported|observed|found|suggests|suggest|indicates|reveals|prior work|previous work)\b",
            re.IGNORECASE,
        ),
        "primary or review source",
    ),
    (
        "mechanistic claim",
        re.compile(
            r"\b(?:causes|drives|leads to|results in|enables|permits|underlies|binds|recruits|activates|suppresses|restores|attenuates|disrupts|converges on)\b",
            re.IGNORECASE,
        ),
        "primary experimental source",
    ),
    (
        "comparative or novelty claim",
        re.compile(r"\b(?:novel|first|unique|better|outperforms|more than|less than|improves)\b", re.IGNORECASE),
        "comparative or benchmark source",
    ),
]


def rel_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root))


def extract_front_matter(text: str) -> tuple[str | None, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, text

    for index in range(1, len(lines)):
        if lines[index].strip() in {"---", "..."}:
            return "\n".join(lines[1:index]), "\n".join(lines[index + 1 :])
    return None, text


def iter_paragraphs(path: Path):
    text = path.read_text(encoding="utf-8")
    _, body = extract_front_matter(text)
    lines = body.splitlines()
    heading = None
    in_code = False
    in_math = False
    in_block = False
    paragraph_lines: list[str] = []
    paragraph_start = 1

    def flush():
        nonlocal paragraph_lines, paragraph_start
        if paragraph_lines:
            yield paragraph_start, heading, " ".join(paragraph_lines).strip()
            paragraph_lines = []

    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if paragraph_lines:
                yield from flush()
            in_code = not in_code
            continue
        if stripped == "$$":
            if paragraph_lines:
                yield from flush()
            in_math = not in_math
            continue
        if stripped.startswith(":::"):
            if paragraph_lines:
                yield from flush()
            in_block = not in_block
            continue
        if in_code or in_math or in_block:
            continue

        heading_match = re.match(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", line)
        if heading_match:
            if paragraph_lines:
                yield from flush()
            heading = heading_match.group(1).strip()
            continue

        if not stripped:
            if paragraph_lines:
                yield from flush()
            continue

        if stripped.startswith((">", "-", "*", "|")) or re.match(r"^\d+\.\s", stripped):
            if paragraph_lines:
                yield from flush()
            continue

        if re.match(r"^[A-Za-z0-9_-]+\s*:\s*$", stripped):
            if paragraph_lines:
                yield from flush()
            continue

        if not paragraph_lines:
            paragraph_start = index
        paragraph_lines.append(stripped)

    if paragraph_lines:
        yield from flush()


def has_citation(sentence: str) -> bool:
    if re.search(r"\[[^\]]*@[\w:-]+[^\]]*\]", sentence):
        return True
    if re.search(r"(?<!\w)@[\w:-]+", sentence):
        return True
    return False


def split_sentences(paragraph: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", paragraph) if part.strip()]


def assess_sentence(sentence: str) -> tuple[list[str], str | None]:
    reasons = []
    suggested_type = None
    if len(sentence) < 35:
        return reasons, suggested_type
    for label, pattern, citation_type in HEURISTICS:
        if pattern.search(sentence):
            reasons.append(label)
            if suggested_type is None:
                suggested_type = citation_type
    return reasons, suggested_type


def scan(path_input: Path) -> dict[str, object]:
    path = path_input.resolve()
    root = path.parent if path.is_file() else path
    qmd_files = [path] if path.is_file() else sorted(root.rglob("*.qmd"))
    gaps = []
    scanned = []

    for qmd_path in qmd_files:
        if any(part in RENDER_DIR_NAMES for part in qmd_path.parts):
            continue
        scanned.append(rel_path(qmd_path, root))
        for line_number, heading, paragraph in iter_paragraphs(qmd_path):
            for sentence in split_sentences(paragraph):
                if has_citation(sentence):
                    continue
                reasons, suggested_type = assess_sentence(sentence)
                if not reasons:
                    continue
                gaps.append(
                    {
                        "file": rel_path(qmd_path, root),
                        "line": line_number,
                        "heading": heading,
                        "sentence": sentence,
                        "reasons": reasons,
                        "suggested_citation_type": suggested_type,
                    }
                )

    return {
        "input_path": str(path_input),
        "root": str(root),
        "files_scanned": scanned,
        "gaps": gaps,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default=".", help="Quarto manuscript file or directory")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    result = scan(Path(args.path))
    if args.pretty:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
