#!/usr/bin/env python3
"""Produce a concise, decision-ready Nsight Systems summary."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("stats_dir", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def find_csv(stats_dir: Path, needle: str) -> Path | None:
    for path in sorted(stats_dir.glob("*.csv")):
        if needle in path.name:
            return path
    return None


def read_csv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.exists() or path.stat().st_size == 0:
        return []
    with path.open(newline="") as fh:
        return list(csv.DictReader(fh))


def parse_float(raw: str | None) -> float:
    if raw is None:
        return 0.0
    text = raw.strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def ns(row: dict[str, str], *keys: str) -> float:
    for key in keys:
        value = parse_float(row.get(key))
        if value:
            if key.endswith("(us)"):
                return value * 1_000.0
            if key == "Time (%)":
                return value
            return value
    return 0.0


@dataclass
class ApiSummary:
    total_time_ns: float = 0.0
    malloc_time_ns: float = 0.0
    memcpy_time_ns: float = 0.0
    launch_time_ns: float = 0.0
    launch_calls: float = 0.0

@dataclass
class KernelSummary:
    total_time_ns: float = 0.0
    total_instances: int = 0
    hottest_instances: int = 0


def summarize_api(api_rows: list[dict[str, str]]) -> ApiSummary:
    summary = ApiSummary()
    for row in api_rows:
        name = row.get("Name", "")
        total = ns(row, "Total Time (ns)", "Total Time (us)")
        calls = ns(row, "Num Calls", "Calls")
        summary.total_time_ns += total
        if "cudaMalloc" in name or "cudaFree" in name:
            summary.malloc_time_ns += total
        if "cudaMemcpy" in name or "cudaMemset" in name:
            summary.memcpy_time_ns += total
        if "cudaLaunchKernel" in name:
            summary.launch_time_ns += total
            summary.launch_calls += calls
    return summary


def summarize_kernels(kernel_rows: list[dict[str, str]]) -> KernelSummary:
    summary = KernelSummary()
    for row in kernel_rows:
        summary.total_time_ns += ns(row, "Total Time (ns)", "Total Time (us)")
        instances = int(parse_float(row.get("Instances")))
        summary.total_instances += instances
        if instances > summary.hottest_instances:
            summary.hottest_instances = instances
    return summary


def dominant_issue(api: ApiSummary, kernel_rows: list[dict[str, str]]) -> tuple[str, list[str], str, list[str]]:
    reasons: list[str] = []
    hints: list[str] = []
    next_step = "Use the paired Nsight Compute run on the hottest steady-state kernel."
    status = "ok"
    kernels = summarize_kernels(kernel_rows)

    api_total = api.total_time_ns if api.total_time_ns > 0.0 else 1.0
    malloc_pct = 100.0 * api.malloc_time_ns / api_total
    memcpy_pct = 100.0 * api.memcpy_time_ns / api_total
    launch_pct = 100.0 * api.launch_time_ns / api_total
    kernel_to_malloc_ratio = kernels.total_time_ns / max(api.malloc_time_ns, 1.0)

    if not kernel_rows:
        status = "rerun"
        reasons.append("No CUDA kernel rows were exported. The run is not usable for timeline decisions.")
        next_step = "Rerun with the full target-side nsys binary and CUDA trace enabled."
        hints.append("missing-kernel-trace")
        return status, reasons, next_step, hints

    if malloc_pct >= 50.0:
        status = "partial"
        hints.append("allocator-churn")
        reasons.append(
            f"Allocator churn dominates the timeline ({malloc_pct:.1f}% of CUDA API time in malloc/free). "
            "This run is not a clean steady-state throughput measurement."
        )
        next_step = "Warm allocations out of the measured loop or lengthen the steady-state phase, then rerun if timing matters."
    elif malloc_pct >= 20.0:
        if kernel_to_malloc_ratio >= 1.5 and memcpy_pct < 10.0 and kernels.hottest_instances >= 100:
            reasons.append(
                f"One-time allocation cost is still visible ({malloc_pct:.1f}% of CUDA API time), "
                "but the steady-state kernel window is long enough that timing is still representative."
            )
        else:
            status = "partial"
            hints.append("allocator-churn")
            reasons.append(
                f"Allocator setup is still too large relative to the steady-state window ({malloc_pct:.1f}% of CUDA API time). "
                "This run is weak evidence for end-to-end timing."
            )
            next_step = "Lengthen the steady-state phase or reduce setup work further, then rerun."

    if memcpy_pct >= 15.0:
        status = "partial"
        hints.append("host-device-traffic")
        reasons.append(
            f"Memcpy or memset activity is material ({memcpy_pct:.1f}% of CUDA API time). "
            "Host-device traffic may be distorting end-to-end timing."
        )
        next_step = "Keep data resident and rerun after removing steady-state transfer traffic."

    if kernels.total_instances < 20 or kernels.hottest_instances < 5:
        status = "partial"
        hints.append("too-few-samples")
        reasons.append(
            f"Kernel sample count is light (total instances={kernels.total_instances}, hottest kernel instances={kernels.hottest_instances}). "
            "This is weak evidence for run-to-run steadiness."
        )
        next_step = "Increase benchmark repeats or isolate a longer steady-state phase, then rerun."

    if launch_pct >= 20.0 and kernel_rows:
        hints.append("launch-overhead")
        reasons.append(
            f"Kernel launches are visible ({launch_pct:.1f}% of CUDA API time). "
            "If the kernels are individually short, consider fusion or CUDA Graph capture."
        )

    if not reasons:
        reasons.append("CUDA kernel rows were exported and the run looks representative enough for first-pass timeline decisions.")

    return status, reasons, next_step, sorted(set(hints))


def format_kernel_line(row: dict[str, str]) -> str:
    name = row.get("Name", "<unknown>")
    time_pct = parse_float(row.get("Time (%)"))
    total_ms = ns(row, "Total Time (ns)") / 1_000_000.0
    instances = int(parse_float(row.get("Instances")))
    avg_us = ns(row, "Avg (ns)") / 1_000.0
    return f"- {name} | time={time_pct:.1f}% total={total_ms:.3f} ms instances={instances} avg={avg_us:.2f} us"


def build_summary(stats_dir: Path) -> dict:
    api_rows = read_csv(find_csv(stats_dir, "cuda_api_sum"))
    kernel_rows = read_csv(find_csv(stats_dir, "cuda_gpu_kern_sum"))
    api = summarize_api(api_rows)
    status, reasons, next_step, hints = dominant_issue(api, kernel_rows)
    api_total = api.total_time_ns if api.total_time_ns > 0.0 else 1.0

    top_kernels = []
    for row in kernel_rows[:5]:
        top_kernels.append(
            {
                "name": row.get("Name", "<unknown>"),
                "time_pct": parse_float(row.get("Time (%)")),
                "total_ms": ns(row, "Total Time (ns)", "Total Time (us)") / 1_000_000.0,
                "instances": int(parse_float(row.get("Instances"))),
                "avg_us": ns(row, "Avg (ns)") / 1_000.0,
            }
        )

    return {
        "tool": "nsys",
        "status": status,
        "trace_valid": bool(kernel_rows),
        "steady_state_timing_valid": status == "ok",
        "needs_rerun_for_timing": status != "ok",
        "measurement_scope": "timeline and setup behavior",
        "reasons": reasons,
        "bottleneck_hints": hints,
        "next_step": next_step,
        "top_kernels": top_kernels,
        "api_signals": {
            "malloc_free_pct": 100.0 * api.malloc_time_ns / api_total,
            "memcpy_memset_pct": 100.0 * api.memcpy_time_ns / api_total,
            "launch_pct": 100.0 * api.launch_time_ns / api_total,
            "launch_calls": api.launch_calls,
        },
        "notes": [
            "Use Nsight Systems to decide whether the benchmark reflects steady-state behavior or mostly setup and transfer costs.",
            "Use benchmark output for throughput numbers. Use Nsight Compute for kernel cause, not timeline validity.",
        ],
    }


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Nsight Systems Decision",
        "",
        f"status: {summary['status']}",
        f"trace_valid: {'yes' if summary['trace_valid'] else 'no'}",
        f"steady_state_timing_valid: {'yes' if summary['steady_state_timing_valid'] else 'no'}",
        f"needs_rerun_for_timing: {'yes' if summary['needs_rerun_for_timing'] else 'no'}",
        f"measurement_scope: {summary['measurement_scope']}",
        "",
        "decision:",
    ]

    for reason in summary["reasons"]:
        lines.append(f"- {reason}")

    lines.extend(["", f"next_step: {summary['next_step']}", ""])

    if summary["top_kernels"]:
        lines.append("top_kernels:")
        for row in summary["top_kernels"]:
            lines.append(
                f"- {row['name']} | time={row['time_pct']:.1f}% total={row['total_ms']:.3f} ms instances={row['instances']} avg={row['avg_us']:.2f} us"
            )
        lines.append("")

    api_signals = summary["api_signals"]
    lines.append("api_signals:")
    lines.append(f"- malloc_free_pct={api_signals['malloc_free_pct']:.1f}")
    lines.append(f"- memcpy_memset_pct={api_signals['memcpy_memset_pct']:.1f}")
    lines.append(f"- launch_pct={api_signals['launch_pct']:.1f}")
    lines.append(f"- launch_calls={api_signals['launch_calls']:.0f}")
    lines.append("")

    lines.append("notes:")
    for note in summary["notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(args.stats_dir)
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to summarize Nsight Systems stats: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
