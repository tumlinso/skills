#!/usr/bin/env python3
"""Summarize simple exported metrics into a coarse V100 kernel classification."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", type=Path)
    args = parser.parse_args()

    with args.csv_path.open(newline="") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        raise SystemExit("no rows")

    row = rows[0]
    dram = float(row.get("dram_pct", 0.0))
    sm = float(row.get("sm_pct", 0.0))
    tc = float(row.get("tensor_pct", 0.0))
    regs = float(row.get("registers_per_thread", 0.0))

    if dram > sm + 20:
        label = "memory-bound"
    elif tc > 20 and sm >= dram:
        label = "compute-bound dense path"
    elif regs > 96:
        label = "register-limited candidate"
    else:
        label = "mixed or unresolved"

    print(f"classification={label}")
    print(f"dram_pct={dram}")
    print(f"sm_pct={sm}")
    print(f"tensor_pct={tc}")
    print(f"registers_per_thread={regs}")


if __name__ == "__main__":
    main()
