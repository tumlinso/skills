#!/usr/bin/env python3
"""Summarize implementation A vs B into a compact comparison verdict."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("compare_dir", type=Path)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--text-out", type=Path, default=None)
    return parser.parse_args()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def pick_primary_metric(results: dict) -> tuple[str | None, float | None]:
    metrics = results.get("metrics") or {}
    preferred_keys = []
    for key, value in metrics.items():
        if isinstance(key, str) and any(token in key.lower() for token in ("throughput", "gib_per_s", "samples_per_s", "items_per_s", "nnz_per_s")):
            try:
                preferred_keys.append((key, float(value)))
            except (TypeError, ValueError):
                continue
    preferred_keys.sort(key=lambda item: item[1], reverse=True)
    return preferred_keys[0] if preferred_keys else (None, None)


def dominant_phase(results: dict) -> dict | None:
    phases = [phase for phase in results.get("phases", []) if isinstance(phase, dict)]
    if not phases:
      return None
    return max(phases, key=lambda phase: float(phase.get("wall_ms", 0.0)))


def build_summary(compare_dir: Path) -> dict:
    compare_config = load_json(compare_dir / "compare_config.json")
    a_results = load_json(compare_dir / "impl_a" / "results.json")
    b_results = load_json(compare_dir / "impl_b" / "results.json")
    metric_a_name, metric_a_value = pick_primary_metric(a_results)
    metric_b_name, metric_b_value = pick_primary_metric(b_results)
    shared_metric = metric_a_name if metric_a_name == metric_b_name else metric_a_name or metric_b_name
    winner = None
    percent_delta = None
    if metric_a_value is not None and metric_b_value is not None and metric_a_value != 0:
        if metric_b_value > metric_a_value:
            winner = compare_config["impl_b_name"]
        elif metric_a_value > metric_b_value:
            winner = compare_config["impl_a_name"]
        else:
            winner = "tie"
        percent_delta = ((metric_b_value - metric_a_value) / metric_a_value) * 100.0

    a_phase = dominant_phase(a_results)
    b_phase = dominant_phase(b_results)
    correctness_ok = bool((a_results.get("checks") or {}).get("valid", False)) and bool((b_results.get("checks") or {}).get("valid", False))
    reasons = []
    if not correctness_ok:
        reasons.append("At least one implementation failed correctness or equivalence checks.")
    if shared_metric is None:
        reasons.append("No shared primary metric was found across both implementations.")
    if not reasons:
        reasons.append("Both implementations produced structured results under one shared comparison contract.")

    dominant_delta = None
    if a_phase and b_phase:
        dominant_delta = {
            "impl_a_phase": str(a_phase.get("name", "<unknown>")),
            "impl_b_phase": str(b_phase.get("name", "<unknown>")),
            "wall_ms_delta": float(b_phase.get("wall_ms", 0.0)) - float(a_phase.get("wall_ms", 0.0)),
        }

    return {
        "tool": "compare-benchmark",
        "status": "ok" if correctness_ok and shared_metric is not None else "partial",
        "comparison_id": compare_config["comparison_id"],
        "impl_a_name": compare_config["impl_a_name"],
        "impl_b_name": compare_config["impl_b_name"],
        "scenario_id": compare_config["scenario_id"],
        "correctness_ok": correctness_ok,
        "primary_metric": shared_metric,
        "impl_a_metric": metric_a_value,
        "impl_b_metric": metric_b_value,
        "winner": winner,
        "percent_delta_vs_a": percent_delta,
        "impl_a_dominant_phase": a_phase,
        "impl_b_dominant_phase": b_phase,
        "dominant_delta": dominant_delta,
        "reasons": reasons,
        "next_step": "Profile both sides if the timing gap is real but the component cause is still unclear.",
    }


def format_summary(summary: dict) -> str:
    lines = [
        "Compare Benchmarks Decision",
        "",
        f"status: {summary['status']}",
        f"comparison_id: {summary['comparison_id']}",
        f"impl_a: {summary['impl_a_name']}",
        f"impl_b: {summary['impl_b_name']}",
        f"scenario_id: {summary['scenario_id']}",
        f"correctness_ok: {'yes' if summary['correctness_ok'] else 'no'}",
    ]
    if summary.get("primary_metric"):
        lines.append(f"primary_metric: {summary['primary_metric']}")
    if summary.get("impl_a_metric") is not None:
        lines.append(f"impl_a_metric: {summary['impl_a_metric']:.6f}")
    if summary.get("impl_b_metric") is not None:
        lines.append(f"impl_b_metric: {summary['impl_b_metric']:.6f}")
    if summary.get("winner"):
        lines.append(f"winner: {summary['winner']}")
    if summary.get("percent_delta_vs_a") is not None:
        lines.append(f"percent_delta_vs_a: {summary['percent_delta_vs_a']:.3f}")
    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason}")
    if summary.get("dominant_delta"):
        delta = summary["dominant_delta"]
        lines.extend(
            [
                "",
                "dominant_component_delta:",
                f"- impl_a_phase={delta['impl_a_phase']}, impl_b_phase={delta['impl_b_phase']}, wall_ms_delta={delta['wall_ms_delta']:.3f}",
            ]
        )
    lines.extend(["", f"next_step: {summary['next_step']}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    summary = build_summary(args.compare_dir)
    text = format_summary(summary)
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
    if args.text_out:
        args.text_out.write_text(text)
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
