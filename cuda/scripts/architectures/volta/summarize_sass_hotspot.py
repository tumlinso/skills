#!/usr/bin/env python3
"""Summarize a focused SASS or objdump section for Volta tuning decisions."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


CATEGORIES = {
    "memory_global": re.compile(r"\b(LD\.G|ST\.G|LDG|STG|ATOM|RED)\b", re.I),
    "memory_shared": re.compile(r"\b(LD\.S|ST\.S|LDS|STS)\b", re.I),
    "tensor": re.compile(r"\b(HMMA|WMMA)\b", re.I),
    "branch": re.compile(r"\b(BRA|JMP|RET|CALL)\b", re.I),
    "barrier": re.compile(r"\b(BAR|MEMBAR|SYNC|SSY)\b", re.I),
    "shuffle_vote": re.compile(r"\b(SHFL|VOTE|MATCH|ACTIVEMASK)\b", re.I),
}


def summarize(text: str) -> dict[str, object]:
    counts = {name: 0 for name in CATEGORIES}
    interesting = []
    total = 0
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        matched = False
        for name, regex in CATEGORIES.items():
            if regex.search(line):
                counts[name] += 1
                matched = True
        if matched:
            interesting.append(line)
            total += 1
    dominant = max(counts, key=counts.get) if any(counts.values()) else "none"
    return {
        "interesting_instruction_lines": total,
        "dominant_category": dominant,
        "counts": counts,
        "sample_lines": interesting[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Focused SASS or objdump text file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    payload = summarize(Path(args.input).read_text(encoding="utf-8"))
    if args.json:
        json.dump(payload, sys.stdout, indent=2)
        print()
        return 0
    print(f"interesting_instruction_lines={payload['interesting_instruction_lines']}")
    print(f"dominant_category={payload['dominant_category']}")
    for key, value in payload["counts"].items():
        print(f"{key}={value}")
    for line in payload["sample_lines"]:
        print(f"sample={line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
