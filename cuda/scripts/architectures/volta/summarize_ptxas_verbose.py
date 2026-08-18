#!/usr/bin/env python3
"""Summarize ptxas verbose output for Volta-native tuning."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


REG_RE = re.compile(r"Used\s+(\d+)\s+registers", re.I)
SMEM_RE = re.compile(r"(\d+)\s+bytes\s+smem", re.I)
CMEM_RE = re.compile(r"(\d+)\s+bytes\s+cmem", re.I)
STACK_RE = re.compile(r"(\d+)\s+bytes stack frame", re.I)
SPILL_STORE_RE = re.compile(r"(\d+)\s+bytes spill stores", re.I)
SPILL_LOAD_RE = re.compile(r"(\d+)\s+bytes spill loads", re.I)
FUNC_RE = re.compile(r"Compiling entry function ['\"]?([^'\":]+)")


def summarize(text: str) -> dict[str, object]:
    rows = []
    current = {"function": "<unknown>", "registers": None, "smem": 0, "cmem": 0, "stack": 0, "spill_stores": 0, "spill_loads": 0}
    saw_data = False
    for line in text.splitlines():
        func = FUNC_RE.search(line)
        if func:
            if saw_data:
                rows.append(current)
            current = {"function": func.group(1), "registers": None, "smem": 0, "cmem": 0, "stack": 0, "spill_stores": 0, "spill_loads": 0}
            saw_data = False
            continue
        matched = False
        for regex, key in (
            (REG_RE, "registers"),
            (SMEM_RE, "smem"),
            (CMEM_RE, "cmem"),
            (STACK_RE, "stack"),
            (SPILL_STORE_RE, "spill_stores"),
            (SPILL_LOAD_RE, "spill_loads"),
        ):
            found = regex.search(line)
            if found:
                current[key] = int(found.group(1))
                matched = True
        saw_data = saw_data or matched
    if saw_data:
        rows.append(current)
    if not rows and text.strip():
        rows.append(current)
    for row in rows:
        spills = row["spill_stores"] + row["spill_loads"]
        if spills:
            row["classification"] = "spill_pressure"
        elif row["registers"] is not None and row["registers"] >= 128:
            row["classification"] = "high_register_pressure"
        else:
            row["classification"] = "clean_or_unknown"
    return {"kernels": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="ptxas verbose stdout or stderr text file.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    payload = summarize(Path(args.input).read_text(encoding="utf-8"))
    if args.json:
        json.dump(payload, sys.stdout, indent=2)
        print()
        return 0
    for row in payload["kernels"]:
        print(
            f"function={row['function']} "
            f"registers={row['registers']} smem={row['smem']} cmem={row['cmem']} "
            f"stack={row['stack']} spill_stores={row['spill_stores']} spill_loads={row['spill_loads']} "
            f"classification={row['classification']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
