#!/usr/bin/env python3
"""Combine crash, sanitizer, and cuda-gdb summaries into one compact verdict."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SEVERITY = {"ok": 0, "partial": 1, "rerun": 2}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crash", type=Path, default=None)
    parser.add_argument("--sanitizer", type=Path, default=None)
    parser.add_argument("--cuda-gdb", type=Path, dest="cuda_gdb", default=None)
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


def choose_next_step(crash: dict | None, sanitizer: dict | None, cuda_gdb: dict | None) -> str:
    for item in (sanitizer, cuda_gdb, crash):
        if item and item.get("status") in {"partial", "rerun"}:
            return str(item.get("next_step", "Collect stronger crash evidence before acting on the result."))
    for item in (sanitizer, cuda_gdb, crash):
        if item and item.get("next_step"):
            return str(item["next_step"])
    return "Inspect the strongest available crash artifact and rerun only after the fix is in place."


def build_summary(crash: dict | None, sanitizer: dict | None, cuda_gdb: dict | None) -> dict:
    if crash is None and sanitizer is None and cuda_gdb is None:
        raise ValueError("Pass at least one debug summary JSON input.")

    reasons: list[str] = []
    for item in (crash, sanitizer, cuda_gdb):
        if item:
            reasons.extend(str(reason) for reason in item.get("reasons", []))

    if not reasons:
        reasons.append("Combined crash summary is based on the available debug artifacts.")

    backtrace_head = []
    source_hint = ""
    limitations: list[str] = []
    if cuda_gdb:
        backtrace_head = list(cuda_gdb.get("backtrace_head", []))[:4]
        source_hint = str(cuda_gdb.get("source_hint") or "")
    for item in (crash, sanitizer, cuda_gdb):
        if item:
            limitations.extend(str(value) for value in item.get("limitations", []))

    return {
        "tool": "combined-crash-summary",
        "status": worst_status(crash, sanitizer, cuda_gdb),
        "conclusive": any(bool(item and item.get("conclusive")) for item in (sanitizer, cuda_gdb, crash)),
        "crash_class": pick_field(
            sanitizer.get("crash_class") if sanitizer else None,
            cuda_gdb.get("crash_class") if cuda_gdb else None,
            crash.get("crash_class") if crash else None,
            default="unknown",
        ),
        "likely_domain": pick_field(
            sanitizer.get("likely_domain") if sanitizer else None,
            cuda_gdb.get("likely_domain") if cuda_gdb else None,
            crash.get("likely_domain") if crash else None,
            default="unknown",
        ),
        "exit_status": crash.get("exit_status") if crash else None,
        "signal": pick_field(
            cuda_gdb.get("signal") if cuda_gdb else None,
            crash.get("signal") if crash else None,
        ),
        "source_hint": source_hint,
        "backtrace_head": backtrace_head,
        "limitations": limitations[:6],
        "next_step": choose_next_step(crash, sanitizer, cuda_gdb),
        "reasons": reasons[:8],
    }


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Combined Crash Decision",
        "",
        f"status: {summary['status']}",
        f"conclusive: {'yes' if summary['conclusive'] else 'no'}",
        f"crash_class: {summary['crash_class']}",
        f"likely_domain: {summary['likely_domain']}",
        f"exit_status: {summary['exit_status'] if summary['exit_status'] is not None else ''}",
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
    if summary.get("limitations"):
        lines.extend(["", "limitations:"])
        for line in summary["limitations"]:
            lines.append(f"- {line}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(load_json(args.crash), load_json(args.sanitizer), load_json(args.cuda_gdb))
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
