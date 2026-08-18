#!/usr/bin/env python3
"""Classify crash, compute-sanitizer, and cuda-gdb outputs into compact summaries."""

from __future__ import annotations

import argparse
import json
import re
import signal as signal_module
import sys
from pathlib import Path


STATUS_SEVERITY = {"ok": 0, "partial": 1, "rerun": 2}

SIGNATURE_RULES = [
    {
        "name": "device-side assert",
        "priority": 90,
        "patterns": [r"device-side assert triggered", r"cuda exception.*device-side assert"],
        "crash_class": "device-assert",
        "likely_domain": "device-assert",
        "next_step": "Rerun with assertions and debug symbols, then use batch cuda-gdb if the failing site is still unclear.",
        "reason": "A device-side assertion was reported.",
    },
    {
        "name": "device memory fault",
        "priority": 85,
        "patterns": [
            r"illegal memory access",
            r"misaligned address",
            r"warp out-of-range address",
            r"invalid __global__ (read|write)",
            r"out of bounds",
            r"memory access error",
        ],
        "crash_class": "device-memory-fault",
        "likely_domain": "device-memory-bug",
        "next_step": "Use compute-sanitizer memcheck output to repair indexing, pointer lifetime, or address calculations before profiling.",
        "reason": "The failure looks like a device memory bug.",
    },
    {
        "name": "launch failure",
        "priority": 75,
        "patterns": [
            r"unspecified launch failure",
            r"invalid configuration argument",
            r"too many resources requested for launch",
            r"an illegal instruction was encountered",
        ],
        "crash_class": "launch-failure",
        "likely_domain": "launch-or-kernel-fault",
        "next_step": "Inspect launch dimensions, shared-memory requests, and deferred kernel faults before returning to optimization work.",
        "reason": "The failure surfaced as a kernel launch or configuration problem.",
    },
    {
        "name": "synchronization fault",
        "priority": 70,
        "patterns": [r"barrier error detected", r"warp diverged", r"synccheck", r"synchronization error"],
        "crash_class": "sync-fault",
        "likely_domain": "sync-bug",
        "next_step": "Use synccheck or repair the warp/block synchronization contract before benchmarking.",
        "reason": "The failure looks like a synchronization bug.",
    },
    {
        "name": "race fault",
        "priority": 68,
        "patterns": [r"race reported", r"hazard", r"data race", r"racecheck"],
        "crash_class": "race-fault",
        "likely_domain": "race-bug",
        "next_step": "Use racecheck findings to repair concurrent accesses before tuning anything else.",
        "reason": "The failure looks like a data race.",
    },
    {
        "name": "initialization fault",
        "priority": 66,
        "patterns": [r"uninitialized", r"initcheck"],
        "crash_class": "initialization-fault",
        "likely_domain": "init-bug",
        "next_step": "Repair uninitialized device state or missing setup before profiling.",
        "reason": "The failure looks like an initialization bug.",
    },
    {
        "name": "host segfault",
        "priority": 60,
        "patterns": [r"segmentation fault", r"sigsegv", r"signal 11"],
        "crash_class": "host-segfault",
        "likely_domain": "host-crash",
        "next_step": "Use batch cuda-gdb to capture a short backtrace and failing source location.",
        "reason": "The failure looks like a host-visible segmentation fault.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["crash", "compute-sanitizer", "cuda-gdb"], required=True)
    parser.add_argument("--stdout", type=Path, default=None)
    parser.add_argument("--stderr", type=Path, default=None)
    parser.add_argument("--log", type=Path, default=None)
    parser.add_argument("--exit-code", type=int, default=None)
    parser.add_argument("--signal", type=str, default="")
    parser.add_argument("--tool", type=str, default="")
    parser.add_argument("--command", type=str, default="")
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def read_text(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return path.read_text(errors="replace")


def normalize_signal(raw: str, exit_code: int | None) -> tuple[str, str | None]:
    text = raw.strip()
    if text:
        if text.isdigit():
            try:
                name = signal_module.Signals(int(text)).name
            except Exception:
                name = f"SIG{text}"
            return text, name
        upper = text.upper()
        return upper.removeprefix("SIG"), upper if upper.startswith("SIG") else f"SIG{upper}"
    if exit_code is not None and exit_code > 128:
        num = exit_code - 128
        try:
            name = signal_module.Signals(num).name
        except Exception:
            name = f"SIG{num}"
        return str(num), name
    return "", None


def summarize_lines(text: str, limit: int = 5) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return []
    return lines[-limit:]


def detect_rule(text: str) -> dict | None:
    chosen: dict | None = None
    lowered = text.lower()
    for rule in SIGNATURE_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, lowered):
                if chosen is None or rule["priority"] > chosen["priority"]:
                    chosen = rule
                break
    return chosen


def detect_error_count(text: str) -> int | None:
    match = re.search(r"error summary:\s*(\d+)\s+errors?", text, flags=re.I)
    if match:
        return int(match.group(1))
    return None


def extract_backtrace_head(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if re.match(r"#\d+", line.strip())][:4]


def extract_host_frames(text: str, limit: int = 4) -> list[str]:
    frames: list[str] = []
    for line in text.splitlines():
        match = re.search(r"Host Frame:\s*(.+)", line)
        if match:
            frames.append(match.group(1).rstrip())
        if len(frames) >= limit:
            break
    return frames


def detect_limitations(text: str) -> list[str]:
    lowered = text.lower()
    limitations: list[str] = []
    if "device not supported" in lowered:
        limitations.append("sanitizer-device-unsupported")
    if "detaching after fork from child process" in lowered:
        limitations.append("debugger-detached-after-fork")
    if "exited normally" in lowered and "no stack" in lowered:
        limitations.append("debugger-no-stack-after-normal-exit")
    return limitations


def extract_source_hint(backtrace: list[str]) -> str | None:
    for line in backtrace:
        match = re.search(r"\bat\s+(.+:\d+)\b", line)
        if match:
            return match.group(1)
        match = re.search(r"\bin\s+(.+:\d+)\b", line)
        if match:
            return match.group(1)
    return None


def build_summary(args: argparse.Namespace) -> dict:
    stdout_text = read_text(args.stdout)
    stderr_text = read_text(args.stderr)
    log_text = read_text(args.log)
    combined_text = "\n".join(part for part in [stderr_text, stdout_text, log_text] if part)
    signal_num, signal_name = normalize_signal(args.signal, args.exit_code)
    matched_rule = detect_rule(combined_text)

    summary = {
        "tool": args.mode,
        "status": "partial",
        "conclusive": False,
        "command": args.command,
        "exit_status": args.exit_code,
        "signal": signal_name or "",
        "crash_class": "unknown",
        "likely_domain": "unknown",
        "next_step": "Inspect the raw logs and rerun with a narrower reproducer.",
        "reasons": [],
        "matched_signatures": [],
        "stderr_tail": summarize_lines(stderr_text),
        "stdout_tail": summarize_lines(stdout_text),
        "backtrace_head": [],
        "host_frames": [],
        "source_hint": None,
        "tool_detail": args.tool or "",
        "limitations": detect_limitations(combined_text),
    }

    if matched_rule is not None:
        summary["crash_class"] = matched_rule["crash_class"]
        summary["likely_domain"] = matched_rule["likely_domain"]
        summary["next_step"] = matched_rule["next_step"]
        summary["matched_signatures"].append(matched_rule["name"])
        summary["reasons"].append(matched_rule["reason"])

    if summary["crash_class"] == "unknown" and signal_name == "SIGSEGV":
        summary["crash_class"] = "host-segfault"
        summary["likely_domain"] = "host-crash"
        summary["next_step"] = "Use batch cuda-gdb to capture a short backtrace and failing source location."
        summary["matched_signatures"].append("SIGSEGV")
        summary["reasons"].append("The process died with SIGSEGV.")

    if args.mode == "crash":
        if args.exit_code == 0:
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["crash_class"] = "no-crash"
            summary["likely_domain"] = "stable-run"
            summary["next_step"] = "The wrapper did not reproduce a crash. Rerun on the real reproducer or move on to normal profiling."
            summary["reasons"] = ["The wrapped command exited cleanly."]
        elif summary["crash_class"] != "unknown":
            summary["status"] = "ok"
            summary["conclusive"] = True
        else:
            summary["next_step"] = "Escalate to batch cuda-gdb because the first-pass crash summary did not isolate a clear failure family."
            summary["reasons"].append("The first-pass crash capture saw a failure but did not match a strong CUDA or host crash signature.")

    elif args.mode == "compute-sanitizer":
        error_count = detect_error_count(log_text)
        summary["error_count"] = error_count
        summary["host_frames"] = extract_host_frames(log_text)
        if not summary["source_hint"] and summary["host_frames"]:
            summary["source_hint"] = summary["host_frames"][0]
        if error_count is not None:
            if error_count == 0:
                summary["status"] = "partial"
                summary["conclusive"] = False
                if summary["crash_class"] == "unknown":
                    summary["likely_domain"] = "unknown"
                summary["next_step"] = "The sanitizer run did not report a device fault. Escalate to batch cuda-gdb if the crash still reproduces."
                summary["reasons"].append("compute-sanitizer reported zero errors.")
            else:
                summary["status"] = "ok"
                summary["conclusive"] = True
                if summary["crash_class"] == "unknown":
                    tool_name = (args.tool or "memcheck").lower()
                    mapping = {
                        "memcheck": ("device-memory-fault", "device-memory-bug"),
                        "racecheck": ("race-fault", "race-bug"),
                        "synccheck": ("sync-fault", "sync-bug"),
                        "initcheck": ("initialization-fault", "init-bug"),
                    }
                    summary["crash_class"], summary["likely_domain"] = mapping.get(
                        tool_name, ("sanitizer-fault", "device-bug")
                    )
                summary["next_step"] = "Apply the sanitizer finding and rerun the binary cleanly before profiling."
                summary["reasons"].append(f"compute-sanitizer reported {error_count} error(s).")
                if "sanitizer-device-unsupported" in summary["limitations"]:
                    summary["status"] = "partial"
                    summary["reasons"].append("compute-sanitizer reported a device-support limitation on this host, so treat the result as crash-family evidence rather than a full instrumented diagnosis.")
                    summary["next_step"] = "Use the reported crash family plus the saved host frames, then rerun with CUDA_LAUNCH_BLOCKING=1 or batch cuda-gdb if the exact failing operation is still unclear."
        else:
            summary["status"] = "partial"
            summary["next_step"] = "The sanitizer log did not expose an error summary. Inspect raw.log and rerun with a smaller reproducer if needed."
            summary["reasons"].append("The sanitizer log did not contain an `ERROR SUMMARY` line.")

    elif args.mode == "cuda-gdb":
        backtrace = extract_backtrace_head(log_text)
        summary["backtrace_head"] = backtrace
        summary["source_hint"] = extract_source_hint(backtrace)
        if not summary["source_hint"] and "debugger-detached-after-fork" in summary["limitations"]:
            summary["source_hint"] = "cuda-gdb detached after a fork before capturing the crashing child"
        signal_match = re.search(r"Program received signal ([A-Z0-9]+)", log_text)
        if signal_match and not summary["signal"]:
            summary["signal"] = signal_match.group(1)
        if summary["crash_class"] == "unknown" and summary["signal"] == "SIGSEGV":
            summary["crash_class"] = "host-segfault"
            summary["likely_domain"] = "host-crash"
            summary["next_step"] = "Use the backtrace to repair the host-side pointer or lifetime bug, then rerun the binary normally."
        if backtrace:
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["next_step"] = "Use the backtrace to repair the identified fault, then rerun the binary cleanly before profiling."
            summary["reasons"].append("cuda-gdb produced a backtrace for the failing process.")
            if summary["source_hint"]:
                summary["reasons"].append(f"Closest source hint: {summary['source_hint']}.")
        else:
            summary["status"] = "partial"
            if "debugger-detached-after-fork" in summary["limitations"]:
                summary["crash_class"] = "debugger-follow-fork-miss"
                summary["likely_domain"] = "debugger-follow-fork-miss"
                summary["next_step"] = "Rerun batch cuda-gdb while following the child process or remove the fork boundary around the reproducer."
                summary["reasons"].append("cuda-gdb detached after a fork and never captured the crashing child.")
            elif "debugger-no-stack-after-normal-exit" in summary["limitations"]:
                summary["next_step"] = "Rerun batch cuda-gdb on a reproducer that still crashes under the debugger, or switch to CUDA_LAUNCH_BLOCKING=1 first."
                summary["reasons"].append("cuda-gdb saw the inferior exit normally and had no stack to report.")
            else:
                summary["next_step"] = "cuda-gdb did not emit a usable backtrace. Inspect raw.log or rerun with a simpler reproducer and debug symbols."
                summary["reasons"].append("cuda-gdb did not produce a clear backtrace.")

    if not summary["reasons"]:
        summary["reasons"].append("No strong signature matched the available output.")

    return summary


def format_summary(summary: dict) -> str:
    lines = [
        "V100 Crash Debug Decision",
        "",
        f"tool: {summary['tool']}",
        f"status: {summary['status']}",
        f"conclusive: {'yes' if summary['conclusive'] else 'no'}",
        f"crash_class: {summary['crash_class']}",
        f"likely_domain: {summary['likely_domain']}",
        f"exit_status: {summary['exit_status'] if summary['exit_status'] is not None else ''}",
        f"signal: {summary['signal']}",
    ]
    if summary.get("tool_detail"):
        lines.append(f"tool_detail: {summary['tool_detail']}")
    if summary.get("error_count") is not None:
        lines.append(f"error_count: {summary['error_count']}")
    if summary.get("source_hint"):
        lines.append(f"source_hint: {summary['source_hint']}")
    lines.extend(["", "decision:"])
    for reason in summary["reasons"]:
        lines.append(f"- {reason}")
    lines.extend(["", f"next_step: {summary['next_step']}"])
    if summary["matched_signatures"]:
        lines.extend(["", "matched_signatures:"])
        for item in summary["matched_signatures"]:
            lines.append(f"- {item}")
    if summary["backtrace_head"]:
        lines.extend(["", "backtrace_head:"])
        for item in summary["backtrace_head"]:
            lines.append(f"- {item}")
    if summary["host_frames"]:
        lines.extend(["", "host_frames:"])
        for item in summary["host_frames"]:
            lines.append(f"- {item}")
    if summary["limitations"]:
        lines.extend(["", "limitations:"])
        for item in summary["limitations"]:
            lines.append(f"- {item}")
    if summary["stderr_tail"]:
        lines.extend(["", "stderr_tail:"])
        for item in summary["stderr_tail"]:
            lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(args)
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(text)
        return 0
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to classify CUDA failure output: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
