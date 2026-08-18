#!/usr/bin/env python3
"""Emit a compact native-V100 benchmark scenario matrix."""

from __future__ import annotations

import argparse
import json
import sys


def build_matrix(label_prefix: str) -> list[dict[str, object]]:
    return [
        {"name": f"{label_prefix}small", "scenario": "small", "intent": "launch_and_glue", "arch": "sm_70"},
        {"name": f"{label_prefix}large-compute", "scenario": "large-compute", "intent": "math_or_tensor_saturation", "arch": "sm_70"},
        {"name": f"{label_prefix}large-transfer", "scenario": "large-transfer", "intent": "host_device_and_pipeline", "arch": "sm_70"},
        {"name": f"{label_prefix}real", "scenario": "real", "intent": "preserve_sparse_skew_and_branch_shape", "arch": "sm_70"},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label-prefix", default="", help="Optional prefix for each scenario name.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()
    matrix = build_matrix(args.label_prefix)
    if args.json:
        json.dump(matrix, sys.stdout, indent=2)
        print()
        return 0
    for item in matrix:
        print(f"{item['name']} scenario={item['scenario']} intent={item['intent']} arch={item['arch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
