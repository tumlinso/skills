#!/usr/bin/env python3
"""Classify native crash, gdb, strace, and perf outputs into compact summaries."""

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
        "name": "asan memory bug",
        "priority": 100,
        "patterns": [
            r"addresssanitizer",
            r"heap-use-after-free",
            r"stack-buffer-overflow",
            r"heap-buffer-overflow",
            r"global-buffer-overflow",
            r"use-after-poison",
        ],
        "crash_class": "asan-memory-bug",
        "likely_domain": "sanitizer-asan",
        "next_step": "Fix the first AddressSanitizer-reported access before chasing later fallout.",
        "reason": "The output contains an AddressSanitizer memory report.",
    },
    {
        "name": "tsan race",
        "priority": 98,
        "patterns": [r"threadsanitizer", r"data race", r"lock-order-inversion"],
        "crash_class": "tsan-race",
        "likely_domain": "sanitizer-tsan",
        "next_step": "Fix the first ThreadSanitizer race or lock-order report, then rerun the same instrumented build.",
        "reason": "The output contains a ThreadSanitizer race report.",
    },
    {
        "name": "ubsan undefined behavior",
        "priority": 96,
        "patterns": [r"undefinedbehaviorsanitizer", r"runtime error:", r"ubsan"],
        "crash_class": "ubsan-undefined-behavior",
        "likely_domain": "sanitizer-ubsan",
        "next_step": "Fix the first UndefinedBehaviorSanitizer report before trusting later symptoms.",
        "reason": "The output contains an UndefinedBehaviorSanitizer report.",
    },
    {
        "name": "uncaught exception",
        "priority": 88,
        "patterns": [r"terminate called after throwing", r"what\(\):", r"std::"],
        "crash_class": "uncaught-exception",
        "likely_domain": "host-exception",
        "next_step": "Inspect the throwing site or exception path in gdb and fix the first uncaught exception.",
        "reason": "The process aborted after throwing an exception.",
    },
    {
        "name": "assertion failure",
        "priority": 84,
        "patterns": [r"assertion [`'\"(].*failed", r"assert failed", r"\bassert\b"],
        "crash_class": "assertion-failure",
        "likely_domain": "host-assert",
        "next_step": "Fix the violated assertion contract or inspect the top frame in gdb.",
        "reason": "The output contains an assertion failure.",
    },
    {
        "name": "segmentation fault",
        "priority": 80,
        "patterns": [r"segmentation fault", r"sigsegv", r"signal 11"],
        "crash_class": "host-segfault",
        "likely_domain": "host-crash",
        "next_step": "Use batch gdb to capture a short backtrace and failing source line.",
        "reason": "The process died with a segmentation-fault style signal.",
    },
    {
        "name": "abort",
        "priority": 76,
        "patterns": [r"\baborted\b", r"sigabrt", r"signal 6"],
        "crash_class": "host-abort",
        "likely_domain": "host-crash",
        "next_step": "Use batch gdb to identify the aborting frame or earlier assertion/exception trigger.",
        "reason": "The process aborted on the host side.",
    },
    {
        "name": "bus error",
        "priority": 74,
        "patterns": [r"bus error", r"sigbus", r"signal 7"],
        "crash_class": "host-bus-error",
        "likely_domain": "host-crash",
        "next_step": "Inspect alignment, mapping, or invalid-address handling with gdb and symbolization.",
        "reason": "The process hit a bus error.",
    },
    {
        "name": "illegal instruction",
        "priority": 72,
        "patterns": [r"illegal instruction", r"sigill", r"signal 4"],
        "crash_class": "illegal-instruction",
        "likely_domain": "host-cpu-feature",
        "next_step": "Inspect the top frame and compiler target settings before rerunning.",
        "reason": "The process executed an illegal instruction.",
    },
    {
        "name": "floating point exception",
        "priority": 70,
        "patterns": [r"floating point exception", r"sigfpe", r"signal 8"],
        "crash_class": "floating-point-exception",
        "likely_domain": "host-arithmetic",
        "next_step": "Inspect the top frame and arithmetic preconditions in gdb.",
        "reason": "The process hit a floating-point exception.",
    },
    {
        "name": "memory pressure",
        "priority": 68,
        "patterns": [r"std::bad_alloc", r"cannot allocate memory", r"out of memory"],
        "crash_class": "memory-pressure",
        "likely_domain": "host-memory",
        "next_step": "Inspect allocation size, growth policy, and input dimensions before deeper tracing.",
        "reason": "The output indicates host-side memory pressure.",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["crash", "gdb", "strace", "perf"], required=True)
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


def normalize_signal(raw: str, exit_code: int | None) -> tuple[str, str]:
    text = raw.strip()
    if text:
        if text.isdigit():
            try:
                return text, signal_module.Signals(int(text)).name
            except Exception:
                return text, f"SIG{text}"
        upper = text.upper()
        if not upper.startswith("SIG"):
            upper = f"SIG{upper}"
        return upper.removeprefix("SIG"), upper
    if exit_code is not None and exit_code > 128:
        num = exit_code - 128
        try:
            return str(num), signal_module.Signals(num).name
        except Exception:
            return str(num), f"SIG{num}"
    return "", ""


def summarize_lines(text: str, limit: int = 5) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return lines[-limit:]


def detect_rule(text: str) -> dict | None:
    lowered = text.lower()
    chosen: dict | None = None
    for rule in SIGNATURE_RULES:
        if any(re.search(pattern, lowered) for pattern in rule["patterns"]):
            if chosen is None or rule["priority"] > chosen["priority"]:
                chosen = rule
    return chosen


def detect_limitations(text: str) -> list[str]:
    lowered = text.lower()
    limitations: list[str] = []
    if "ptrace: operation not permitted" in lowered or "operation not permitted" in lowered and "ptrace" in lowered:
        limitations.append("ptrace-blocked")
    if "no stack" in lowered:
        limitations.append("debugger-no-stack")
    if "perf_event_open" in lowered and "operation not permitted" in lowered:
        limitations.append("perf-permission-denied")
    if "not enough privileges" in lowered and "perf" in lowered:
        limitations.append("perf-permission-denied")
    if "failed to open" in lowered and "perf.data" in lowered:
        limitations.append("perf-output-failure")
    return limitations


def extract_backtrace_head(text: str) -> list[str]:
    return [line.rstrip() for line in text.splitlines() if re.match(r"#\d+\s", line.strip())][:6]


def extract_source_hint(lines: list[str]) -> str:
    for line in lines:
        match = re.search(r"\bat\s+(.+:\d+)\b", line)
        if match:
            return match.group(1)
        match = re.search(r"\bfrom\s+(.+:\d+)\b", line)
        if match:
            return match.group(1)
    return ""


def parse_strace_failures(text: str) -> list[str]:
    failures: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if " = -1 " in stripped:
            failures.append(stripped)
        elif stripped.startswith("--- SIG"):
            failures.append(stripped)
    return failures[-5:]


def classify_strace_failures(failures: list[str]) -> tuple[str, str, str]:
    joined = "\n".join(failures)
    lowered = joined.lower()
    if " enoent " in lowered:
        return (
            "missing-path",
            "runtime-path",
            "Fix the missing file, shared object, config path, or executable named by the final ENOENT failure.",
        )
    if " eacces " in lowered or " eperm " in lowered:
        return (
            "permission-failure",
            "runtime-permission",
            "Fix the permission boundary or execution context before rerunning.",
        )
    if " enoexec " in lowered:
        return (
            "exec-format-failure",
            "runtime-loader",
            "Fix the interpreter, binary format, or execution target named by the failing execve.",
        )
    if " sigsegv" in lowered or " sigabrt" in lowered:
        return (
            "signal-after-syscall",
            "host-crash",
            "Use the syscall context plus a short gdb backtrace to identify the failing user frame.",
        )
    return (
        "syscall-failure",
        "runtime-boundary",
        "Inspect the last failing syscall in the trace before opening the full log.",
    )


def parse_perf_csv(text: str) -> dict[str, str]:
    counters: dict[str, str] = {}
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 3:
            continue
        value = parts[0]
        event = parts[2]
        if not event or value in {"<not counted>", "<not supported>", ""}:
            continue
        counters[event] = value
    cycles = _parse_float(counters.get("cycles", ""))
    instructions = _parse_float(counters.get("instructions", ""))
    if cycles and instructions is not None:
        counters["ipc"] = f"{instructions / cycles:.3f}"
    return counters


def _parse_float(value: str) -> float | None:
    if not value:
        return None
    cleaned = value.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def build_summary(args: argparse.Namespace) -> dict:
    stdout_text = read_text(args.stdout)
    stderr_text = read_text(args.stderr)
    log_text = read_text(args.log)
    combined_text = "\n".join(part for part in [stderr_text, stdout_text, log_text] if part)
    _, signal_name = normalize_signal(args.signal, args.exit_code)
    matched_rule = detect_rule(combined_text)

    summary = {
        "tool": args.mode,
        "status": "partial",
        "conclusive": False,
        "command": args.command,
        "exit_status": args.exit_code,
        "signal": signal_name,
        "crash_class": "unknown",
        "likely_domain": "unknown",
        "next_step": "Inspect the strongest available summary and rerun with a narrower reproducer.",
        "reasons": [],
        "matched_signatures": [],
        "stderr_tail": summarize_lines(stderr_text),
        "stdout_tail": summarize_lines(stdout_text),
        "backtrace_head": [],
        "source_hint": "",
        "limitations": detect_limitations(combined_text),
        "failed_syscalls": [],
        "perf_counters": {},
        "tool_detail": args.tool or "",
    }

    if matched_rule is not None:
        summary["crash_class"] = matched_rule["crash_class"]
        summary["likely_domain"] = matched_rule["likely_domain"]
        summary["next_step"] = matched_rule["next_step"]
        summary["matched_signatures"].append(matched_rule["name"])
        summary["reasons"].append(matched_rule["reason"])

    if args.mode == "crash":
        if args.exit_code == 0:
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["crash_class"] = "no-crash"
            summary["likely_domain"] = "stable-run"
            summary["next_step"] = "The wrapped command exited cleanly. Move to perf or another route only if the user still needs diagnosis."
            summary["reasons"] = ["The wrapped command exited cleanly."]
        elif summary["crash_class"] != "unknown":
            summary["status"] = "ok"
            summary["conclusive"] = True
        elif signal_name:
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["crash_class"] = signal_name.lower()
            summary["likely_domain"] = "host-crash"
            summary["next_step"] = "Use batch gdb to capture a short backtrace and failing source line."
            summary["reasons"].append(f"The process exited due to {signal_name}.")
        else:
            summary["reasons"].append("The process failed but the first-pass crash capture did not isolate a strong fault family.")
            summary["next_step"] = "Escalate to a sanitizer build or batch gdb depending on whether memory corruption is likely."

    elif args.mode == "gdb":
        backtrace = extract_backtrace_head(log_text)
        summary["backtrace_head"] = backtrace
        summary["source_hint"] = extract_source_hint(backtrace)
        signal_match = re.search(r"Program received signal (SIG[A-Z]+)", log_text)
        if signal_match:
            summary["signal"] = signal_match.group(1)
        if backtrace:
            summary["status"] = "ok"
            summary["conclusive"] = True
            if summary["crash_class"] == "unknown" and summary["signal"]:
                summary["crash_class"] = summary["signal"].lower()
                summary["likely_domain"] = "host-crash"
            summary["reasons"].append("The gdb log contains a usable backtrace.")
            summary["next_step"] = "Fix the top user frame first, then rerun the same reproducer."
        elif "ptrace-blocked" in summary["limitations"]:
            summary["status"] = "rerun"
            summary["next_step"] = "Rerun gdb where ptrace is permitted, then capture a short backtrace again."
            summary["reasons"].append("The debugger could not attach because ptrace was blocked.")
        else:
            summary["status"] = "partial"
            summary["next_step"] = "Adjust the reproducer or follow the crashing child process more narrowly, then rerun gdb."
            summary["reasons"].append("The gdb run did not produce a usable backtrace.")

    elif args.mode == "strace":
        failures = parse_strace_failures(log_text)
        summary["failed_syscalls"] = failures
        if failures:
            crash_class, likely_domain, next_step = classify_strace_failures(failures)
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["crash_class"] = crash_class
            summary["likely_domain"] = likely_domain
            summary["next_step"] = next_step
            summary["reasons"].append("The syscall trace contains a narrow final failure sequence.")
        else:
            summary["status"] = "partial"
            summary["next_step"] = "If the runtime boundary still looks suspicious, rerun with a tighter reproducer or return to gdb."
            summary["reasons"].append("The trace did not expose a strong final failing syscall pattern.")

    elif args.mode == "perf":
        counters = parse_perf_csv(log_text)
        summary["perf_counters"] = counters
        if "perf-permission-denied" in summary["limitations"]:
            summary["status"] = "rerun"
            summary["next_step"] = "Rerun perf where perf_event access is allowed or lower perf_event_paranoid."
            summary["reasons"].append("Perf collection was blocked by permissions.")
        elif counters:
            summary["status"] = "ok"
            summary["conclusive"] = True
            summary["crash_class"] = "perf-stat-summary"
            summary["likely_domain"] = "cpu-runtime"
            summary["next_step"] = "If the binary is still too slow after this first pass, escalate to perf record/report or a comparison benchmark."
            summary["reasons"].append("Perf stat counters were collected successfully.")
            if counters.get("ipc"):
                summary["reasons"].append(f"Estimated IPC is {counters['ipc']}.")
        else:
            summary["status"] = "partial"
            summary["next_step"] = "Inspect perf stderr and rerun on a simpler stable command if counters were not collected."
            summary["reasons"].append("Perf did not yield parsable counters.")

    return summary


def format_summary(summary: dict) -> str:
    title = {
        "crash": "Native Crash Summary",
        "gdb": "Native GDB Summary",
        "strace": "Native Strace Summary",
        "perf": "Native Perf Summary",
    }.get(summary["tool"], "Native Debug Summary")

    lines = [
        title,
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

    if summary["matched_signatures"]:
        lines.extend(["", "matched_signatures:"])
        for item in summary["matched_signatures"]:
            lines.append(f"- {item}")

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
        summary = build_summary(args)
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(text)
        return 0
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to classify native debug output: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
