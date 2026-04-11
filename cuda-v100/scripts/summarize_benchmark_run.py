#!/usr/bin/env python3
"""Summarize structured benchmark artifacts into compact text and JSON."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Benchmark run directory or results.json path")
    parser.add_argument("--json-out", type=Path, default=None, help="Optional summary JSON output path")
    parser.add_argument("--text-out", type=Path, default=None, help="Optional summary text output path")
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def resolve_paths(path: Path) -> tuple[Path, Path]:
    if path.is_dir():
        return path / "run_config.json", path / "results.json"
    if path.name == "results.json":
        return path.parent / "run_config.json", path
    raise ValueError("Pass a benchmark run directory or results.json path.")


def as_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def top_metric_lines(metrics: dict[str, object]) -> list[str]:
    preferred = []
    for key, value in metrics.items():
        if not isinstance(key, str):
            continue
        if any(token in key.lower() for token in ("throughput", "gib_per_s", "nnz_per_s", "mnnz_per_s", "samples_per_s")):
            preferred.append((key, as_float(value)))
    preferred.sort(key=lambda item: item[1], reverse=True)
    return [f"{key}={value:.3f}" for key, value in preferred[:3]]


def phase_signature(phase: dict) -> dict:
    metrics = phase.get("metrics") or {}
    counters = phase.get("counters") or {}
    return {
        "name": str(phase.get("name", "<unknown>")),
        "wall_ms": as_float(phase.get("wall_ms")),
        "steady_state": bool(phase.get("steady_state", False)),
        "measured_iterations": as_int(phase.get("measured_iterations"), 0),
        "warmup_iterations": as_int(phase.get("warmup_iterations"), 0),
        "metric_highlights": top_metric_lines(metrics),
        "counters": {str(key): value for key, value in counters.items()},
    }


def build_summary(run_config: dict, results: dict) -> dict:
    phases = [phase_signature(phase) for phase in results.get("phases", []) if isinstance(phase, dict)]
    reasons: list[str] = []
    next_step = "Run Nsight Systems first on the dominant steady-state phase, then Nsight Compute on the hottest kernel."
    status = "ok"

    if not phases:
        status = "rerun"
        reasons.append("No measured phases were emitted. The benchmark is not using the standard results contract yet.")

    steady_phases = [phase for phase in phases if phase["steady_state"]]
    if not steady_phases:
        if status != "rerun":
            status = "partial"
        reasons.append("No phase is marked `steady_state=true`, so throughput timing is weak evidence for real steady-state behavior.")

    dominant = max(phases, key=lambda phase: phase["wall_ms"], default=None)
    dominant_steady = max(steady_phases, key=lambda phase: phase["wall_ms"], default=dominant)

    if dominant_steady is not None and dominant_steady["measured_iterations"] < 3:
        if status == "ok":
            status = "partial"
        reasons.append(
            f"Dominant steady-state phase `{dominant_steady['name']}` has only {dominant_steady['measured_iterations']} measured iterations."
        )

    dataset_tier = str(run_config.get("dataset_tier", "unknown"))
    dataset_id = run_config.get("dataset_id")
    dataset_manifest = run_config.get("dataset_manifest")
    if dataset_tier == "unknown":
        if status == "ok":
            status = "partial"
        reasons.append("`dataset_tier` is missing, so the run cannot be classified as smoke, stress, or real-data evidence.")
    if dataset_tier == "real" and not dataset_id and not dataset_manifest:
        if status == "ok":
            status = "partial"
        reasons.append("Real-data run is missing `dataset_id` or `dataset_manifest`.")

    visible_devices = run_config.get("visible_device_ids") or run_config.get("devices") or []
    if isinstance(visible_devices, list) and len(visible_devices) > 1 and not run_config.get("topology"):
        if status == "ok":
            status = "partial"
        reasons.append("Multi-GPU run does not record topology or placement assumptions.")

    checks = results.get("checks") or {}
    if isinstance(checks, dict) and checks.get("valid") is False:
        status = "rerun"
        reasons.append("Benchmark checks reported invalid results.")
        next_step = "Fix correctness before trusting any timing or profiler output."

    if not reasons:
        reasons.append("Structured benchmark artifacts are present and the run looks representative enough for first-pass benchmarking decisions.")

    summary_metrics = top_metric_lines(results.get("metrics") or {})
    return {
        "tool": "benchmark",
        "status": status,
        "steady_state_timing_valid": status == "ok" and bool(steady_phases),
        "needs_rerun_for_timing": status != "ok",
        "benchmark_id": str(run_config.get("benchmark_id", run_config.get("workload_family", "unknown-benchmark"))),
        "workload_family": str(run_config.get("workload_family", "unknown")),
        "dataset_tier": dataset_tier,
        "dataset_id": dataset_id,
        "dataset_manifest": dataset_manifest,
        "visible_device_ids": visible_devices,
        "topology": run_config.get("topology"),
        "dominant_phase": dominant,
        "dominant_steady_phase": dominant_steady,
        "summary_metrics": summary_metrics,
        "checks": checks,
        "phases": phases,
        "reasons": reasons,
        "next_step": next_step,
    }


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Benchmark Decision",
        "",
        f"status: {summary['status']}",
        f"steady_state_timing_valid: {'yes' if summary['steady_state_timing_valid'] else 'no'}",
        f"needs_rerun_for_timing: {'yes' if summary['needs_rerun_for_timing'] else 'no'}",
        f"benchmark_id: {summary['benchmark_id']}",
        f"workload_family: {summary['workload_family']}",
        f"dataset_tier: {summary['dataset_tier']}",
    ]

    if summary.get("dataset_id"):
        lines.append(f"dataset_id: {summary['dataset_id']}")
    if summary.get("dataset_manifest"):
        lines.append(f"dataset_manifest: {summary['dataset_manifest']}")
    if summary.get("visible_device_ids"):
        lines.append(f"visible_device_ids: {summary['visible_device_ids']}")
    if summary.get("topology"):
        lines.append(f"topology: {summary['topology']}")

    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason}")

    dominant = summary.get("dominant_steady_phase") or summary.get("dominant_phase")
    if dominant:
        lines.extend(
            [
                "",
                "dominant_phase:",
                f"- {dominant['name']} | wall_ms={dominant['wall_ms']:.3f} | measured_iterations={dominant['measured_iterations']} | steady_state={'yes' if dominant['steady_state'] else 'no'}",
            ]
        )
        for item in dominant.get("metric_highlights", []):
            lines.append(f"  metric: {item}")

    if summary.get("summary_metrics"):
        lines.extend(["", "benchmark_metrics:"])
        for item in summary["summary_metrics"]:
            lines.append(f"- {item}")

    lines.extend(["", f"next_step: {summary['next_step']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        run_config_path, results_path = resolve_paths(args.path)
        if not run_config_path.exists() or not results_path.exists():
            raise FileNotFoundError("Expected run_config.json and results.json.")
        summary = build_summary(load_json(run_config_path), load_json(results_path))
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        if args.text_out is not None:
            args.text_out.write_text(text)
        sys.stdout.write(text)
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to summarize benchmark run: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
