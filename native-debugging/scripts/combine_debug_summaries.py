#!/usr/bin/env python3
"""Combine native crash, gdb, strace, and perf summaries into one compact verdict."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SEVERITY = {"ok": 0, "partial": 1, "rerun": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash", type=Path, default=None)
    parser.add_argument("--gdb", type=Path, default=None)
    parser.add_argument("--strace", type=Path, default=None)
    parser.add_argument("--perf", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--text-out", type=Path, default=None)
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


def pick_field(*values: str | None, default: str = "") -> str:
    for value in values:
        if value and value != "unknown":
            return str(value)
    return default


def choose_next_step(*items: dict | None) -> str:
    for item in items:
        if item and item.get("status") in {"partial", "rerun"} and item.get("next_step"):
            return str(item["next_step"])
    for item in items:
        if item and item.get("next_step"):
            return str(item["next_step"])
    return "Inspect the strongest available summary and rerun only after the first fix is in place."


def build_summary(crash: dict | None, gdb: dict | None, strace: dict | None, perf: dict | None) -> dict:
    if all(item is None for item in (crash, gdb, strace, perf)):
        raise ValueError("Pass at least one debug summary JSON input.")

    reasons: list[str] = []
    limitations: list[str] = []
    for item in (crash, gdb, strace, perf):
        if item:
            reasons.extend(str(reason) for reason in item.get("reasons", []))
            limitations.extend(str(limitation) for limitation in item.get("limitations", []))

    if not reasons:
        reasons.append("Combined summary is based on the available debug artifacts.")

    source_hint = ""
    backtrace_head: list[str] = []
    if gdb:
        source_hint = str(gdb.get("source_hint") or "")
        backtrace_head = list(gdb.get("backtrace_head", []))[:6]

    failed_syscalls = list(strace.get("failed_syscalls", []))[:5] if strace else []
    perf_counters = dict(perf.get("perf_counters", {})) if perf else {}

    return {
        "tool": "combined-debug-summary",
        "status": worst_status(crash, gdb, strace, perf),
        "conclusive": any(bool(item and item.get("conclusive")) for item in (crash, gdb, strace, perf)),
        "crash_class": pick_field(
            gdb.get("crash_class") if gdb else None,
            crash.get("crash_class") if crash else None,
            strace.get("crash_class") if strace else None,
            perf.get("crash_class") if perf else None,
            default="unknown",
        ),
        "likely_domain": pick_field(
            gdb.get("likely_domain") if gdb else None,
            crash.get("likely_domain") if crash else None,
            strace.get("likely_domain") if strace else None,
            perf.get("likely_domain") if perf else None,
            default="unknown",
        ),
        "signal": pick_field(
            gdb.get("signal") if gdb else None,
            crash.get("signal") if crash else None,
        ),
        "source_hint": source_hint,
        "backtrace_head": backtrace_head,
        "failed_syscalls": failed_syscalls,
        "perf_counters": perf_counters,
        "limitations": limitations[:8],
        "next_step": choose_next_step(gdb, crash, strace, perf),
        "reasons": reasons[:10],
    }


def format_summary(summary: dict) -> str:
    lines = [
        "Native Combined Debug Decision",
        "",
        f"status: {summary['status']}",
        f"conclusive: {'yes' if summary['conclusive'] else 'no'}",
        f"crash_class: {summary['crash_class']}",
        f"likely_domain: {summary['likely_domain']}",
        f"signal: {summary['signal']}",
    ]
    if summary.get("source_hint"):
        lines.append(f"source_hint: {summary['source_hint']}")

    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason}")
    lines.extend(["", f"next_step: {summary['next_step']}"])

    if summary["backtrace_head"]:
        lines.extend(["", "backtrace_head:"])
        for line in summary["backtrace_head"]:
            lines.append(f"- {line}")

    if summary["failed_syscalls"]:
        lines.extend(["", "failed_syscalls:"])
        for line in summary["failed_syscalls"]:
            lines.append(f"- {line}")

    if summary["perf_counters"]:
        lines.extend(["", "perf_counters:"])
        for key in sorted(summary["perf_counters"]):
            lines.append(f"- {key}: {summary['perf_counters'][key]}")

    if summary["limitations"]:
        lines.extend(["", "limitations:"])
        for item in summary["limitations"]:
            lines.append(f"- {item}")

    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(
            load_json(args.crash),
            load_json(args.gdb),
            load_json(args.strace),
            load_json(args.perf),
        )
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        if args.text_out is not None:
            args.text_out.write_text(text)
        sys.stdout.write(text)
        return 0
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to combine debug summaries: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
