#!/usr/bin/env python3
"""Filter objdump-style text down to one symbol and interesting instruction lines."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FUNC_LABEL_RE = re.compile(r"^[0-9a-fA-F]+\s+<([^>]+)>:$")
INTERESTING = {
    "memory": re.compile(r"\b(ld|st|movm|cp\.async|tma|prefetch|atom|red)\b", re.I),
    "branch": re.compile(r"\b(bra|jmp|call|ret|ssy|sync|bar|mbarrier)\b", re.I),
    "control": re.compile(r"\b(setp|selp|vote|shfl|activemask|match)\b", re.I),
}


def slice_symbol(lines: list[str], symbol: str) -> list[str]:
    start = None
    end = len(lines)
    for idx, line in enumerate(lines):
        match = FUNC_LABEL_RE.match(line.strip())
        if match and match.group(1) == symbol:
            start = idx
            continue
        if start is not None and match:
            end = idx
            break
        if start is None and symbol in line:
            start = max(0, idx - 4)
    if start is None:
        return []
    return lines[start:end]


def keep_lines(lines: list[str], categories: set[str], context: int) -> list[str]:
    if not lines:
        return []
    keep = set()
    for idx, line in enumerate(lines):
        if FUNC_LABEL_RE.match(line.strip()):
            keep.add(idx)
            continue
        if any(INTERESTING[name].search(line) for name in categories):
            for nearby in range(max(0, idx - context), min(len(lines), idx + context + 1)):
                keep.add(nearby)
    return [line for idx, line in enumerate(lines) if idx in keep]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="objdump-like text file.")
    parser.add_argument("--symbol", required=True, help="Function or symbol to keep.")
    parser.add_argument(
        "--category",
        action="append",
        choices=sorted(INTERESTING),
        help="Interesting line category. Repeat as needed. Default: all.",
    )
    parser.add_argument("--context", type=int, default=1, help="Context lines around interesting instructions.")
    parser.add_argument("--json", action="store_true", help="Emit a JSON summary.")
    args = parser.parse_args()

    source = Path(args.input).resolve()
    lines = source.read_text(encoding="utf-8").splitlines()
    symbol_lines = slice_symbol(lines, args.symbol)
    categories = set(args.category or INTERESTING)
    filtered = keep_lines(symbol_lines, categories, args.context)

    if args.json:
        payload = {
            "input": str(source),
            "symbol": args.symbol,
            "categories": sorted(categories),
            "matched_lines": len(filtered),
            "total_symbol_lines": len(symbol_lines),
            "lines": filtered,
        }
        json.dump(payload, sys.stdout, indent=2)
        print()
        return 0

    for line in filtered:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
