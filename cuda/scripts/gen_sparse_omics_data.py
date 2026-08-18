#!/usr/bin/env python3
"""Generate synthetic sparse omics-like matrices with skewed nnz/row."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, required=True)
    parser.add_argument("--cols", type=int, required=True)
    parser.add_argument("--target-nnz", type=int, default=0)
    parser.add_argument("--density", type=float, default=0.0)
    parser.add_argument("--distribution", choices=["uniform", "pareto", "two_level"], default="pareto")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--format", choices=["mtx", "json", "both"], default="both")
    return parser.parse_args()


def compute_target_nnz(rows: int, cols: int, target_nnz: int, density: float) -> int:
    if target_nnz > 0:
        return target_nnz
    if density > 0.0:
        return max(1, int(rows * cols * density))
    raise ValueError("Pass either --target-nnz or --density.")


def build_row_counts(rows: int, cols: int, total_nnz: int, distribution: str, rng: random.Random) -> list[int]:
    weights = []
    if distribution == "uniform":
        weights = [1.0] * rows
    elif distribution == "pareto":
        weights = [rng.paretovariate(2.0) for _ in range(rows)]
    elif distribution == "two_level":
        for _ in range(rows):
            if rng.random() < 0.15:
                weights.append(6.0 + rng.random() * 4.0)
            else:
                weights.append(0.5 + rng.random() * 1.5)
    else:
        raise ValueError(f"Unsupported distribution: {distribution}")

    total_weight = sum(weights)
    counts = [min(cols, int(total_nnz * weight / total_weight)) for weight in weights]
    assigned = sum(counts)

    while assigned < total_nnz:
        idx = rng.randrange(rows)
        if counts[idx] < cols:
            counts[idx] += 1
            assigned += 1
    while assigned > total_nnz:
        idx = rng.randrange(rows)
        if counts[idx] > 0:
            counts[idx] -= 1
            assigned -= 1
    return counts


def draw_value(rng: random.Random) -> int:
    threshold = rng.random()
    if threshold < 0.55:
        return 1
    if threshold < 0.78:
        return 2
    if threshold < 0.90:
        return 3
    if threshold < 0.96:
        return 4
    return 5 + rng.randrange(6)


def percentile(sorted_values: list[int], pct: float) -> int:
    if not sorted_values:
        return 0
    pos = min(len(sorted_values) - 1, max(0, int(round((len(sorted_values) - 1) * pct))))
    return sorted_values[pos]


def write_matrix_market(path: Path, rows: int, cols: int, records: list[tuple[int, int, int]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        fh.write("%%MatrixMarket matrix coordinate integer general\n")
        fh.write(f"{rows} {cols} {len(records)}\n")
        for row, col, value in records:
            fh.write(f"{row} {col} {value}\n")


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    total_nnz = compute_target_nnz(args.rows, args.cols, args.target_nnz, args.density)
    row_counts = build_row_counts(args.rows, args.cols, total_nnz, args.distribution, rng)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records: list[tuple[int, int, int]] = []
    row_ptr = [0]
    col_idx: list[int] = []
    values: list[int] = []

    for row in range(args.rows):
        nnz = row_counts[row]
        cols = sorted(rng.sample(range(args.cols), nnz)) if nnz > 0 else []
        for col in cols:
            value = draw_value(rng)
            records.append((row + 1, col + 1, value))
            col_idx.append(col)
            values.append(value)
        row_ptr.append(len(col_idx))

    sorted_counts = sorted(row_counts)
    metadata = {
        "rows": args.rows,
        "cols": args.cols,
        "nnz": len(records),
        "distribution": args.distribution,
        "seed": args.seed,
        "row_nnz_percentiles": {
            "p50": percentile(sorted_counts, 0.50),
            "p90": percentile(sorted_counts, 0.90),
            "p99": percentile(sorted_counts, 0.99),
            "max": sorted_counts[-1] if sorted_counts else 0,
        },
        "notes": [
            "Generated for V100 sparse-omics benchmarking.",
            "Rows represent cells; columns represent genes or peaks.",
            "Use the row nnz percentiles to reason about warp imbalance and row binning.",
        ],
    }

    if args.format in {"mtx", "both"}:
        write_matrix_market(args.output_dir / "matrix.mtx", args.rows, args.cols, records)
    if args.format in {"json", "both"}:
        payload = {
            "metadata": metadata,
            "csr": {
                "row_ptr": row_ptr,
                "col_idx": col_idx,
                "values": values,
            },
        }
        (args.output_dir / "matrix.json").write_text(json.dumps(payload) + "\n")

    (args.output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
