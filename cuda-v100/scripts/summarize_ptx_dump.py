#!/usr/bin/env python3
"""Summarize focused PTX/SASS dump artifacts for Volta hot-path inspection."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class FunctionUsage:
    name: str
    arch: str = ""
    registers: int | None = None
    shared_mem_bytes: int | None = None
    constant_mem_bytes: int | None = None
    stack_frame_bytes: int | None = None
    spill_stores_bytes: int | None = None
    spill_loads_bytes: int | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, help="Run directory produced by dump_ptx_hotspot.sh")
    parser.add_argument("--json-out", type=Path, default=None)
    return parser.parse_args()


def read_run_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def parse_ptx_header(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    version = ""
    target = ""
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(".version "):
            version = stripped.split(None, 1)[1]
        elif stripped.startswith(".target "):
            target = stripped.split(None, 1)[1]
        if version and target:
            break
    return {"ptx_version": version, "ptx_target": target}


def parse_function_usage(text: str) -> list[FunctionUsage]:
    functions: list[FunctionUsage] = []
    current: FunctionUsage | None = None

    compile_re = re.compile(r"Compiling entry function '([^']+)' for '([^']+)'")
    props_re = re.compile(r"Function properties for ([^\s]+)")
    stack_re = re.compile(
        r"(\d+) bytes stack frame,\s+(\d+) bytes spill stores,\s+(\d+) bytes spill loads"
    )
    used_re = re.compile(
        r"Used (\d+) registers(?:,\s*(\d+) bytes smem)?(?:,\s*(\d+) bytes cmem\[0\])?"
    )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = compile_re.search(line)
        if match:
            if current is not None:
                functions.append(current)
            current = FunctionUsage(name=match.group(1), arch=match.group(2))
            continue
        match = props_re.search(line)
        if match and current is None:
            current = FunctionUsage(name=match.group(1))
            continue
        match = stack_re.search(line)
        if match:
            if current is None:
                current = FunctionUsage(name="unknown")
            current.stack_frame_bytes = int(match.group(1))
            current.spill_stores_bytes = int(match.group(2))
            current.spill_loads_bytes = int(match.group(3))
            continue
        match = used_re.search(line)
        if match:
            if current is None:
                current = FunctionUsage(name="unknown")
            current.registers = int(match.group(1))
            if match.group(2):
                current.shared_mem_bytes = int(match.group(2))
            if match.group(3):
                current.constant_mem_bytes = int(match.group(3))
            continue

    if current is not None:
        functions.append(current)
    return functions


def choose_focus(functions: list[FunctionUsage], symbol: str) -> FunctionUsage | None:
    if symbol:
        for function in functions:
            if function.name == symbol or symbol in function.name:
                return function
    return functions[0] if functions else None


def build_summary(path: Path) -> dict:
    run_env = read_run_env(path / "run.env")
    source_path = Path(run_env.get("source_path", ""))
    input_kind = run_env.get("input_kind", "")
    symbol = run_env.get("symbol", "")
    full_ptx = path / "full.ptx"
    full_cubin = path / "kernel.cubin"
    full_cuobjdump = path / "full.cuobjdump.sass"
    full_nvdisasm = path / "full.nvdisasm.sass"
    focused_ptx = path / "focused.ptx"
    focused_cuobjdump = path / "focused.cuobjdump.sass"
    focused_nvdisasm = path / "focused.nvdisasm.sass"

    if not full_ptx.exists() or not full_cubin.exists():
        return {
            "tool": "ptx-dump-summary",
            "status": "rerun",
            "arch": run_env.get("arch", ""),
            "input_kind": input_kind,
            "source_path": str(source_path),
            "symbol": symbol,
            "reasons": ["Missing PTX or cubin artifact."],
            "next_step": "Rerun the dump wrapper and confirm the focused source compiles cleanly for sm_70.",
        }

    compile_text = ""
    for candidate in ("compile.stdout.txt", "compile.stderr.txt", "ptx_compile.stderr.txt"):
        candidate_path = path / candidate
        if candidate_path.exists():
            compile_text += candidate_path.read_text() + "\n"
    functions = parse_function_usage(compile_text)
    focus = choose_focus(functions, symbol)
    ptx_meta = parse_ptx_header(full_ptx)
    focus_requested = bool(symbol)
    focused_ready = focused_ptx.exists() or focused_cuobjdump.exists() or focused_nvdisasm.exists()

    reasons: list[str] = []
    notes: list[str] = []
    status = "ok"

    hot_path_isolation = "likely" if focus_requested else "unknown"
    if focus_requested and not focused_ready:
        status = "partial"
        reasons.append("A focused symbol was requested but no focused artifacts were emitted.")
    elif focus_requested:
        reasons.append("Focused PTX/SASS artifacts were emitted for the requested symbol.")
    else:
        status = "partial"
        reasons.append("No symbol filter was requested, so the dump likely includes a full translation unit.")

    arch = run_env.get("arch", "")
    ptx_target = ptx_meta.get("ptx_target", "")
    if arch and arch != "sm_70":
        status = "partial"
        reasons.append(f"Wrapper target is {arch}, not sm_70.")
    else:
        reasons.append("Wrapper target is sm_70.")
    if ptx_target and "sm_70" not in ptx_target and "compute_70" not in ptx_target:
        status = "partial"
        reasons.append(f"PTX target header is {ptx_target}, not a Volta target.")

    if focus and focus.registers is not None and focus.registers >= 96:
        notes.append("Registers are high enough to recheck residency versus spills on V100.")
    if focus and ((focus.spill_loads_bytes or 0) > 0 or (focus.spill_stores_bytes or 0) > 0):
        notes.append("Spills are present; inspect live ranges before chasing occupancy.")
    if focus and (focus.shared_mem_bytes or 0) > 48 * 1024:
        notes.append("Shared memory exceeds 48 KB; verify the kernel explicitly opts into dynamic shared memory.")

    warnings = []
    for line in compile_text.splitlines():
        if "warning" in line.lower():
            warnings.append(line.strip())
    if warnings:
        notes.extend(list(dict.fromkeys(warnings))[:4])

    artifacts = {
        "full_ptx": str(full_ptx),
        "full_cubin": str(full_cubin),
        "full_cuobjdump_sass": str(full_cuobjdump),
        "full_nvdisasm_sass": str(full_nvdisasm),
    }
    if focused_ptx.exists():
        artifacts["focused_ptx"] = str(focused_ptx)
    if focused_cuobjdump.exists():
        artifacts["focused_cuobjdump_sass"] = str(focused_cuobjdump)
    if focused_nvdisasm.exists():
        artifacts["focused_nvdisasm_sass"] = str(focused_nvdisasm)

    next_step = "Inspect the focused SASS first, then only the full dump if the focus view is insufficient."
    if status == "partial" and not focus_requested:
        next_step = "Rerun with --symbol and an isolated hot-path harness to keep PTX and SASS bounded."
    elif status == "partial" and focus_requested and not focused_ready:
        next_step = "Check the symbol name or simplify the focused harness so the target kernel can be isolated."

    return {
        "tool": "ptx-dump-summary",
        "status": status,
        "arch": arch,
        "input_kind": input_kind,
        "source_path": str(source_path),
        "symbol": symbol,
        "hot_path_isolation": hot_path_isolation,
        "focused_artifacts": focused_ready,
        "ptx_version": ptx_meta.get("ptx_version", ""),
        "ptx_target": ptx_target,
        "focus_function": asdict(focus) if focus else {},
        "functions": [asdict(function) for function in functions],
        "artifacts": artifacts,
        "reasons": reasons,
        "notes": notes[:6],
        "next_step": next_step,
    }


def format_summary(summary: dict) -> str:
    focus = summary.get("focus_function") or {}
    lines = [
        "V100 PTX Dump Decision",
        "",
        f"status: {summary.get('status', '')}",
        f"arch: {summary.get('arch', '')}",
        f"input_kind: {summary.get('input_kind', '')}",
        f"symbol: {summary.get('symbol', '')}",
        f"hot_path_isolation: {summary.get('hot_path_isolation', '')}",
        f"focused_artifacts: {'yes' if summary.get('focused_artifacts') else 'no'}",
        f"ptx_version: {summary.get('ptx_version', '')}",
        f"ptx_target: {summary.get('ptx_target', '')}",
    ]
    if focus:
        lines.extend(
            [
                "",
                "focus_function:",
                f"- name: {focus.get('name', '')}",
                f"- registers: {focus.get('registers', '')}",
                f"- shared_mem_bytes: {focus.get('shared_mem_bytes', '')}",
                f"- stack_frame_bytes: {focus.get('stack_frame_bytes', '')}",
                f"- spill_stores_bytes: {focus.get('spill_stores_bytes', '')}",
                f"- spill_loads_bytes: {focus.get('spill_loads_bytes', '')}",
            ]
        )
    lines.extend(["", "decision:"])
    for reason in summary.get("reasons", []):
        lines.append(f"- {reason}")
    if summary.get("notes"):
        lines.extend(["", "notes:"])
        for note in summary["notes"]:
            lines.append(f"- {note}")
    lines.extend(["", f"next_step: {summary.get('next_step', '')}"])
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        summary = build_summary(args.path)
        text = format_summary(summary)
        if args.json_out is not None:
            args.json_out.write_text(json.dumps(summary, indent=2) + "\n")
        sys.stdout.write(text)
        return 0
    except Exception as exc:  # pragma: no cover
        sys.stderr.write(f"Failed to summarize PTX dump: {exc}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
