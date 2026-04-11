#!/usr/bin/env python3
"""Inspect sparse matrix summary data and emit layout hints for V100 workflows.

Input can be JSON with fields like:
{
  "rows": 100000,
  "cols": 20000,
  "nnz": 8000000,
  "row_nnz_mean": 80,
  "row_nnz_p95": 300,
  "row_nnz_p99": 1200,
  "feature_passes": 5,
  "row_passes": 8
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_summary(path: Path) -> dict:
    return json.loads(path.read_text())


def recommend_layout(summary: dict) -> str:
    row_passes = int(summary.get("row_passes", 0))
    feature_passes = int(summary.get("feature_passes", 0))
    if feature_passes > max(2, row_passes // 2):
        return "CSC or dual CSR+CSC"
    return "CSR"


def recommend_dense_boundary(summary: dict) -> str:
    density = float(summary.get("nnz", 0)) / max(1, int(summary.get("rows", 1)) * int(summary.get("cols", 1)))
    if density > 0.15:
        return "consider earlier dense projection"
    return "stay sparse until projection or aggregation clearly shrinks the problem"


def skew_flag(summary: dict) -> str:
    mean = float(summary.get("row_nnz_mean", 0.0))
    p99 = float(summary.get("row_nnz_p99", 0.0))
    if mean <= 0:
        return "unknown"
    ratio = p99 / mean
    if ratio >= 8:
        return "severe row skew: bin rows aggressively"
    if ratio >= 3:
        return "moderate row skew: row bins likely useful"
    return "row skew not dominant"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("summary_json", type=Path)
    args = parser.parse_args()

    summary = load_summary(args.summary_json)
    print(f"layout: {recommend_layout(summary)}")
    print(f"dense_boundary: {recommend_dense_boundary(summary)}")
    print(f"row_skew: {skew_flag(summary)}")


if __name__ == "__main__":
    main()
