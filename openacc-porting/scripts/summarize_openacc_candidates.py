#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import load_candidates, render_markdown_summary, summarize_candidates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize OpenACC candidate regions from structured notes.")
    parser.add_argument("--input", required=True, type=Path, help="JSON file with candidate notes.")
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="markdown",
        help="Output format.",
    )
    parser.add_argument("--output", type=Path, help="Optional output path. Defaults to stdout.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize_candidates(load_candidates(args.input))

    if args.format == "json":
        payload = json.dumps(summary, indent=2) + "\n"
    else:
        payload = render_markdown_summary(summary)

    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
