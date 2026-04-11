#!/usr/bin/env python3
"""Produce a concise, decision-ready Nsight Compute summary."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path


NUMERIC_COLUMNS = {
    "duration_ns": [
        "gpu__time_duration.sum",
        "gpu__time_duration.avg",
    ],
    "dram_pct": ["dram__throughput.avg.pct_of_peak_sustained_elapsed"],
    "sm_pct": ["sm__throughput.avg.pct_of_peak_sustained_elapsed"],
    "tensor_pct": [
        "smsp__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_elapsed",
        "sm__pipe_tensor_cycles_active.avg.pct_of_peak_sustained_elapsed",
    ],
    "occupancy": [
        "launch__occupancy_per_sm",
        "sm__warps_active.avg.pct_of_peak_sustained_active",
    ],
    "registers_per_thread": ["launch__registers_per_thread"],
    "shared_mem_bytes": [
        "launch__shared_mem_per_block_allocated",
        "launch__shared_mem_per_block",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Run directory or raw.csv path")
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def parse_float(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = raw.strip().replace(",", "")
    if not text or text.lower() in {"nan", "n/a", "--"}:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def normalize_occupancy(metric_name: str, value: float) -> float:
    if "pct_of_peak" in metric_name:
        return value / 100.0
    return value


def resolve_paths(path: Path) -> tuple[Path, Path | None]:
    if path.is_dir():
        csv_path = path / "raw.csv"
        env_path = path / "run.env"
        return csv_path, env_path if env_path.exists() else None
    env_path = path.parent / "run.env"
    return path, env_path if env_path.exists() else None


def read_run_env(path: Path | None) -> dict[str, str]:
    if path is None or not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


@dataclass
class KernelSummary:
    name: str
    samples: int = 0
    total_duration_ns: float = 0.0
    dram_weighted: float = 0.0
    sm_weighted: float = 0.0
    tensor_weighted: float = 0.0
    occupancy_weighted: float = 0.0
    registers_weighted: float = 0.0
    shared_weighted: float = 0.0
    weight_sum: float = 0.0

    def add_metric(self, row: dict[str, str]) -> None:
        duration = None
        for key in NUMERIC_COLUMNS["duration_ns"]:
            duration = parse_float(row.get(key))
            if duration is not None:
                break
        if duration is None:
            duration = 1.0

        self.samples += 1
        self.total_duration_ns += duration

        def add_weighted(bucket: str, attr: str) -> None:
            for metric_name in NUMERIC_COLUMNS[bucket]:
                value = parse_float(row.get(metric_name))
                if value is None:
                    continue
                if bucket == "occupancy":
                    value = normalize_occupancy(metric_name, value)
                setattr(self, attr, getattr(self, attr) + value * duration)
                break

        add_weighted("dram_pct", "dram_weighted")
        add_weighted("sm_pct", "sm_weighted")
        add_weighted("tensor_pct", "tensor_weighted")
        add_weighted("occupancy", "occupancy_weighted")
        add_weighted("registers_per_thread", "registers_weighted")
        add_weighted("shared_mem_bytes", "shared_weighted")
        self.weight_sum += duration

    def avg(self, attr: str) -> float | None:
        if self.weight_sum <= 0.0:
            return None
        value = getattr(self, attr)
        if value == 0.0:
            return None
        return value / self.weight_sum


def classify_kernel(kernel: KernelSummary) -> tuple[str, str]:
    dram = kernel.avg("dram_weighted")
    sm = kernel.avg("sm_weighted")
    tensor = kernel.avg("tensor_weighted")
    occ = kernel.avg("occupancy_weighted")
    regs = kernel.avg("registers_weighted")
    shm = kernel.avg("shared_weighted")

    if dram is not None and sm is not None and (dram >= 60.0 and sm <= 50.0 or dram >= 40.0 and sm <= 25.0 or dram >= 4.0 * max(sm, 1.0)):
        return "memory-bound", "Reduce HBM traffic, improve coalescing, or fuse memory passes."
    if occ is not None and regs is not None and occ < 0.35 and regs >= 96.0:
        return "register-limited", "Try smaller tiles, shorter live ranges, or a capped-register experiment."
    if shm is not None and shm > 48 * 1024:
        return "shared-memory-limited", "Confirm shared reuse is worth the occupancy tradeoff."
    if sm is not None and sm >= 60.0:
        if tensor is not None and tensor < 15.0 and re.search(r"gemm|mma|matmul|attention|qkv", kernel.name, re.I):
            return "compute-path mismatch", "Recheck Tensor Core eligibility, dtype, and multiples-of-8 alignment."
        return "compute-heavy", "Inspect Tensor Core use and arithmetic pipeline efficiency."
    return "mixed", "Pair this with Nsight Systems and the benchmark output before changing the kernel."


def build_summary(path: Path) -> dict:
    csv_path, env_path = resolve_paths(path)
    if not csv_path.exists() or csv_path.stat().st_size == 0:
        return {
            "tool": "ncu",
            "status": "rerun",
            "counter_valid": False,
            "timing_valid": False,
            "needs_more_data": True,
            "measurement_scope": "kernel counters",
            "reasons": ["raw.csv is missing or empty."],
            "next_step": "Rerun Nsight Compute and verify the report exported raw CSV.",
            "hot_kernel": {},
            "top_kernels": [],
            "notes": [],
        }

    with csv_path.open(newline="") as fh:
        rows = list(csv.DictReader(fh))

    kernels: dict[str, KernelSummary] = {}
    for row in rows:
        kernel_name = (row.get("Kernel Name") or "").strip()
        if not kernel_name:
            continue
        summary = kernels.setdefault(kernel_name, KernelSummary(name=kernel_name))
        summary.add_metric(row)

    if not kernels:
        return {
            "tool": "ncu",
            "status": "rerun",
            "counter_valid": False,
            "timing_valid": False,
            "needs_more_data": True,
            "measurement_scope": "kernel counters",
            "reasons": ["The exported CSV did not contain recognizable kernel rows."],
            "next_step": "Rerun Nsight Compute with raw CSV export enabled.",
            "hot_kernel": {},
            "top_kernels": [],
            "notes": [],
        }

    env = read_run_env(env_path)
    ordered = sorted(kernels.values(), key=lambda item: item.total_duration_ns, reverse=True)
    total_duration_ns = sum(item.total_duration_ns for item in ordered) or 1.0
    hot = ordered[0]
    hot_class, hot_action = classify_kernel(hot)
    limited_samples = hot.samples < 3 or len(ordered) < 1
    missing_primary_signal = hot.avg("dram_weighted") is None and hot_class in {"mixed", "compute-heavy"}
    status = "ok"
    if limited_samples or missing_primary_signal:
        status = "partial"

    reasons = [
        "Nsight Compute is valid for kernel-cause diagnosis here, but not for throughput timing because replay changes runtime.",
        f"Hottest kernel class: {hot_class}.",
        f"Primary next move: {hot_action}",
    ]
    if limited_samples:
        reasons.append("- Kernel sample count is light. Rerun with more repeated hot launches if you need stronger confidence.")
    if missing_primary_signal:
        reasons.append("- DRAM throughput was not exported for the hottest kernel, so memory-vs-compute classification is weak. Rerun with the compact V100 metric list or a heavier set.")

    top_kernels = []
    for kernel in ordered[:5]:
        share = 100.0 * kernel.total_duration_ns / total_duration_ns
        klass, action = classify_kernel(kernel)
        dram = kernel.avg("dram_weighted")
        sm = kernel.avg("sm_weighted")
        occ = kernel.avg("occupancy_weighted")
        regs = kernel.avg("registers_weighted")
        top_kernels.append(
            {
                "name": kernel.name,
                "share_pct": share,
                "samples": kernel.samples,
                "class": klass,
                "next_step": action,
                "dram_pct": dram,
                "sm_pct": sm,
                "tensor_pct": kernel.avg("tensor_weighted"),
                "occupancy": occ,
                "registers_per_thread": regs,
            }
        )

    return {
        "tool": "ncu",
        "status": status,
        "counter_valid": True,
        "timing_valid": False,
        "needs_more_data": limited_samples,
        "measurement_scope": "kernel counters",
        "collection_set": env.get("set"),
        "launch_count": env.get("launch_count"),
        "reasons": reasons,
        "hot_kernel": top_kernels[0] if top_kernels else {"class": hot_class, "next_step": hot_action},
        "top_kernels": top_kernels,
        "next_step": hot_action,
        "notes": [
            "Use benchmark output or Nsight Systems for throughput comparisons.",
            "Use Nsight Compute to decide whether poor performance comes from bytes moved, compute path choice, registers, or shared memory.",
        ],
    }


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Nsight Compute Decision",
        "",
        f"status: {summary['status']}",
        f"counter_valid: {'yes' if summary['counter_valid'] else 'no'}",
        f"timing_valid: {'yes' if summary['timing_valid'] else 'no'}",
        f"needs_more_data: {'yes' if summary['needs_more_data'] else 'no'}",
        f"measurement_scope: {summary['measurement_scope']}",
    ]

    if summary.get("collection_set"):
        lines.append(f"collection_set: {summary['collection_set']}")
    if summary.get("launch_count"):
        lines.append(f"launch_count: {summary['launch_count']}")

    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason.lstrip('- ')}")

    lines.extend(["", "top_kernels:"])
    for kernel in summary["top_kernels"]:
        parts = [
            f"- {kernel['name']}",
            f"share={kernel['share_pct']:.1f}%",
            f"samples={kernel['samples']}",
            f"class={kernel['class']}",
        ]
        if kernel.get("dram_pct") is not None:
            parts.append(f"dram={kernel['dram_pct']:.1f}%")
        if kernel.get("sm_pct") is not None:
            parts.append(f"sm={kernel['sm_pct']:.1f}%")
        if kernel.get("occupancy") is not None:
            parts.append(f"occ={kernel['occupancy']:.2f}")
        if kernel.get("registers_per_thread") is not None:
            parts.append(f"regs={kernel['registers_per_thread']:.0f}")
        lines.append(" | ".join(parts))
        lines.append(f"  next: {kernel['next_step']}")

    lines.extend(["", "notes:"])
    for note in summary["notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(args.path)
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to summarize Nsight Compute CSV: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
