#!/usr/bin/env python3
"""Combine benchmark and profiler summaries for implementation A vs B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--nsys-a", type=Path, default=None)
    parser.add_argument("--nsys-b", type=Path, default=None)
    parser.add_argument("--ncu-a", type=Path, default=None)
    parser.add_argument("--ncu-b", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--text-out", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path | None) -> dict | None:
    return json.loads(path.read_text()) if path is not None and path.exists() else None


def main() -> int:
    args = parse_args()
    benchmark = load_json(args.benchmark)
    nsys_a = load_json(args.nsys_a)
    nsys_b = load_json(args.nsys_b)
    ncu_a = load_json(args.ncu_a)
    ncu_b = load_json(args.ncu_b)
    summary = {
        "tool": "combined-compare-summary",
        "benchmark": benchmark,
        "nsys_a": nsys_a,
        "nsys_b": nsys_b,
        "ncu_a": ncu_a,
        "ncu_b": ncu_b,
        "status": benchmark.get("status", "partial") if benchmark else "partial",
        "comparison_id": benchmark.get("comparison_id") if benchmark else None,
        "next_step": "Inspect raw profiler artifacts only if the compact summaries still disagree or remain inconclusive.",
    }
    lines = [
        "Combined Compare Decision",
        "",
        f"status: {summary['status']}",
        f"comparison_id: {summary['comparison_id']}",
        f"next_step: {summary['next_step']}",
    ]
    text = "\n".join(lines) + "\n"
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
    if args.text_out:
        args.text_out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
