#!/usr/bin/env python3
"""Initialize a comparison run directory with config and wrapper placeholders."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--impl-a", required=True, help="Implementation A name")
    parser.add_argument("--impl-b", required=True, help="Implementation B name")
    parser.add_argument("--scenario-id", default="default")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--profile-friendly", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out = args.output_dir
    (out / "impl_a").mkdir(parents=True, exist_ok=True)
    (out / "impl_b").mkdir(parents=True, exist_ok=True)
    config = {
        "comparison_id": f"{args.impl_a}-vs-{args.impl_b}",
        "impl_a_name": args.impl_a,
        "impl_b_name": args.impl_b,
        "scenario_id": args.scenario_id,
        "warmup": args.warmup,
        "repeats": args.repeats,
        "profile_friendly": args.profile_friendly,
        "mutex_path": "${COMPARE_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/compare_benchmarks.lock}",
    }
    (out / "compare_config.json").write_text(json.dumps(config, indent=2) + "\n")
    (out / "impl_a" / "wrapper_notes.txt").write_text("Populate implementation A wrapper here.\n")
    (out / "impl_b" / "wrapper_notes.txt").write_text("Populate implementation B wrapper here.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
