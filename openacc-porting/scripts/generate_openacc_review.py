#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import load_candidates, render_review_markdown, summarize_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or refresh an openacc-review.md artifact.")
    parser.add_argument("--scope", required=True, help="Short scope statement for the review artifact.")
    parser.add_argument("--output", required=True, type=Path, help="Markdown file to write.")
    parser.add_argument(
        "--candidate-json",
        type=Path,
        help="Structured candidate input or a prior summary JSON. If omitted, write a template review.",
    )
    return parser.parse_args()


def load_summary(path: Path | None) -> dict:
    if path is None:
        return {"counts": {"easy to port": 0, "possible with restructuring": 0, "poor OpenACC target": 0},
                "candidates": [],
                "shared_blockers": [],
                "directive_families": []}

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and {"counts", "candidates", "shared_blockers", "directive_families"} <= set(data):
        return data
    return summarize_candidates(load_candidates(path))


def main() -> int:
    args = parse_args()
    summary = load_summary(args.candidate_json)
    content = render_review_markdown(args.scope, summary)
    args.output.write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
