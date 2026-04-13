#!/usr/bin/env python3
"""Compare dominant phases or component timings from two result files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("impl_a_results", type=Path)
    parser.add_argument("impl_b_results", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def phase_map(results: dict) -> dict[str, float]:
    mapping = {}
    for phase in results.get("phases", []):
        if isinstance(phase, dict):
            mapping[str(phase.get("name", "<unknown>"))] = float(phase.get("wall_ms", 0.0))
    return mapping


def main() -> int:
    args = parse_args()
    a = phase_map(load_json(args.impl_a_results))
    b = phase_map(load_json(args.impl_b_results))
    all_keys = sorted(set(a) | set(b))
    if not all_keys:
        print("No comparable phases found.")
        return 0
    diffs = [(key, b.get(key, 0.0) - a.get(key, 0.0)) for key in all_keys]
    diffs.sort(key=lambda item: abs(item[1]), reverse=True)
    key, delta = diffs[0]
    print(f"largest_component_delta: {key} delta_ms={delta:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
