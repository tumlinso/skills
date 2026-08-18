#!/usr/bin/env python3
"""Combine benchmark and profiler summaries into one compact interpretation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SEVERITY = {"ok": 0, "partial": 1, "rerun": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=None, help="Benchmark summary JSON")
    parser.add_argument("--nsys", type=Path, default=None, help="Nsight Systems summary JSON")
    parser.add_argument("--ncu", type=Path, default=None, help="Nsight Compute summary JSON")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional combined JSON output")
    parser.add_argument("--text-out", type=Path, default=None, help="Optional combined text output")
    return parser.parse_args()


def load_json(path: Path | None) -> dict | None:
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text())


def worst_status(*items: dict | None) -> str:
    worst = "ok"
    for item in items:
        if item is None:
            continue
        status = str(item.get("status", "ok"))
        if SEVERITY.get(status, 0) > SEVERITY.get(worst, 0):
            worst = status
    return worst


def detect_bottleneck(benchmark: dict | None, nsys: dict | None, ncu: dict | None) -> str:
    if nsys:
        hints = {str(item) for item in nsys.get("bottleneck_hints", [])}
        if "allocator-churn" in hints:
            return "setup or allocator noise"
        if "host-device-traffic" in hints:
            return "PCIe or staging traffic"
        if "launch-overhead" in hints:
            return "launch overhead"
    if ncu:
        hot = ncu.get("hot_kernel") or {}
        klass = str(hot.get("class", ""))
        if klass:
            return klass
    if benchmark:
        dominant = benchmark.get("dominant_steady_phase") or benchmark.get("dominant_phase") or {}
        if dominant:
            return f"phase `{dominant.get('name', '<unknown>')}` dominates"
    return "unresolved"


def choose_next_step(benchmark: dict | None, nsys: dict | None, ncu: dict | None) -> str:
    for item in (nsys, ncu, benchmark):
        if item and item.get("status") == "rerun":
            return str(item.get("next_step", "Rerun with cleaner steady-state evidence."))
    for item in (nsys, ncu, benchmark):
        if item and item.get("status") == "partial":
            return str(item.get("next_step", "Collect stronger evidence before locking in a conclusion."))
    for item in (ncu, nsys, benchmark):
        if item and item.get("next_step"):
            return str(item["next_step"])
    return "Profile the dominant phase more deeply or compare against the fastest plausible alternative."


def recommend_route(benchmark: dict | None, nsys: dict | None, ncu: dict | None) -> tuple[str, str]:
    for item in (benchmark, nsys, ncu):
        if item and item.get("status") == "rerun":
            return "rerun", "At least one artifact says the measurement must be rerun."
    if nsys and nsys.get("recommended_route"):
        route = str(nsys["recommended_route"])
        if route in {"pipeline", "fusion", "graphs", "rerun"}:
            return route, str(nsys.get("recommended_route_reason", "Timeline summary dominated the route decision."))
    if ncu and ncu.get("recommended_route"):
        return str(ncu["recommended_route"]), str(ncu.get("recommended_route_reason", "Kernel summary dominated the route decision."))
    if benchmark and benchmark.get("workload_balance") == "transfer-dominant":
        return "pipeline", "Benchmark balance says transfer or staging dominates."
    return "native", "No profiler artifact forced a narrower route."


def build_summary(benchmark: dict | None, nsys: dict | None, ncu: dict | None) -> dict:
    if benchmark is None and nsys is None and ncu is None:
        raise ValueError("Pass at least one summary JSON input.")

    reasons: list[str] = []
    if benchmark:
        reasons.extend(str(item) for item in benchmark.get("reasons", []))
    if nsys:
        reasons.extend(str(item) for item in nsys.get("reasons", []))
    if ncu:
        hot = ncu.get("hot_kernel") or {}
        if hot.get("class"):
            reasons.append(f"Hottest kernel class from Nsight Compute: {hot['class']}.")
    if not reasons:
        reasons.append("Combined summary is based on the available benchmark and profiler artifacts.")

    route, route_reason = recommend_route(benchmark, nsys, ncu)

    return {
        "tool": "combined-benchmark-summary",
        "status": worst_status(benchmark, nsys, ncu),
        "benchmark_id": benchmark.get("benchmark_id") if benchmark else None,
        "workload_family": benchmark.get("workload_family") if benchmark else None,
        "dataset_tier": benchmark.get("dataset_tier") if benchmark else None,
        "scenario_kind": benchmark.get("scenario_kind") if benchmark else None,
        "workload_balance": benchmark.get("workload_balance") if benchmark else None,
        "dominant_bottleneck": detect_bottleneck(benchmark, nsys, ncu),
        "recommended_route": route,
        "recommended_route_reason": route_reason,
        "next_step": choose_next_step(benchmark, nsys, ncu),
        "benchmark": benchmark,
        "nsys": nsys,
        "ncu": ncu,
        "reasons": reasons[:8],
    }


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Combined Benchmark Decision",
        "",
        f"status: {summary['status']}",
    ]
    if summary.get("benchmark_id"):
        lines.append(f"benchmark_id: {summary['benchmark_id']}")
    if summary.get("workload_family"):
        lines.append(f"workload_family: {summary['workload_family']}")
    if summary.get("dataset_tier"):
        lines.append(f"dataset_tier: {summary['dataset_tier']}")
    if summary.get("scenario_kind"):
        lines.append(f"scenario_kind: {summary['scenario_kind']}")
    if summary.get("workload_balance"):
        lines.append(f"workload_balance: {summary['workload_balance']}")
    lines.append(f"dominant_bottleneck: {summary['dominant_bottleneck']}")
    lines.append(f"recommended_route: {summary['recommended_route']}")
    lines.append(f"recommended_route_reason: {summary['recommended_route_reason']}")
    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason}")
    lines.extend(["", f"next_step: {summary['next_step']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(load_json(args.benchmark), load_json(args.nsys), load_json(args.ncu))
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        if args.text_out is not None:
            args.text_out.write_text(text)
        sys.stdout.write(text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to combine benchmark summaries: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
