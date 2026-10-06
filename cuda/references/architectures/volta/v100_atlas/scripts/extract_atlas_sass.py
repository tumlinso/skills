#!/usr/bin/env python3
"""Extract selected E02/E37 kernels from an sm_70 atlas_logic binary.

This is an offline, CPU-only inspection helper. It hashes the supplied binary,
uses the verified CUDA 12.9 cuobjdump by default, and writes selected SASS plus
a machine-readable opcode inventory. It does not launch or load the binary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


DEFAULT_CUOBJDUMP = Path(
    "/opt/nvidia/hpc_sdk/Linux_x86_64/26.1/cuda/12.9/bin/cuobjdump"
)
TARGET_FUNCTIONS = {
    "dependent_add_kernel": "dependent_add_kernel",
    "independent_add_kernel_8": "independent_add_kernelILi8",
    "loop_control_clock_kernel": "loop_control_clock_kernel",
    "lop3_boolop_kernel": "lop3_boolop_kernel",
    "lop3_and_boolop_kernel": "lop3_and_boolop_kernel",
}
OPCODE_PATTERNS = {
    "IADD3": re.compile(r"\bIADD3(?:\.[A-Z0-9_.]+)?\b"),
    "IMAD": re.compile(r"\bIMAD(?:\.[A-Z0-9_.]+)?\b"),
    "LOP3_LUT": re.compile(r"\bLOP3\.LUT\b"),
    "PLOP3_LUT": re.compile(r"\bPLOP3\.LUT\b"),
    "ISETP": re.compile(r"\bISETP(?:\.[A-Z0-9_.]+)?\b"),
    "SEL": re.compile(r"\bSEL(?:\.[A-Z0-9_.]+)?\b"),
    "CS2R": re.compile(r"\bCS2R\b"),
}
RELEVANT_INSTRUCTION = re.compile(
    r"\b(?:IADD3|IMAD|LOP3\.LUT|PLOP3\.LUT|ISETP|SEL|CS2R)(?:\.[A-Z0-9_.]+)?\b"
)


def run_checked(argv: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(argv, check=False, text=True, capture_output=True)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"command failed ({result.returncode}): {' '.join(argv)}\n{detail}")
    return result


def binary_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def listed_symbols(listing: str) -> list[str]:
    symbols: list[str] = []
    for line in listing.splitlines():
        match = re.search(r"SASS text section\s+\d+\s*:\s*(\S+)", line)
        if not match:
            continue
        name = match.group(1)
        if name.startswith("x-"):
            name = name[2:]
        name = re.sub(r"\.sm_70\.elf\.bin$", "", name)
        symbols.append(name)
    return symbols


def exact_sass(cuobjdump: Path, binary: Path, symbol: str) -> tuple[str, str]:
    result = run_checked(
        [str(cuobjdump), "--dump-sass", "--gpu-architecture", "sm_70",
         "--function", symbol, str(binary)]
    )
    headers = re.findall(r"^\s*Function\s*:\s*(\S+)\s*$", result.stdout, re.MULTILINE)
    if headers != [symbol]:
        raise RuntimeError(
            f"expected exactly function {symbol!r}, cuobjdump returned {headers!r}"
        )
    # Keep the selected function block only, excluding unrelated fatbin
    # metadata and any subsequent function should cuobjdump behavior change.
    start = re.search(r"^\s*Function\s*:\s*" + re.escape(symbol) + r"\s*$",
                      result.stdout, re.MULTILINE)
    assert start is not None
    body = result.stdout[start.start():]
    body = re.split(r"\n\s*Function\s*:", body, maxsplit=1)[0]
    return body.rstrip() + "\n", result.stderr


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True, type=Path, help="built atlas_logic executable")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--cuobjdump", type=Path, default=DEFAULT_CUOBJDUMP)
    args = parser.parse_args()

    binary = args.binary.expanduser().resolve()
    cuobjdump = args.cuobjdump.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not binary.is_file():
        raise RuntimeError(f"binary does not exist: {binary}")
    if not cuobjdump.is_file():
        raise RuntimeError(f"cuobjdump does not exist: {cuobjdump}")
    output_dir.mkdir(parents=True, exist_ok=True)

    version = run_checked([str(cuobjdump), "--version"])
    listing = run_checked([str(cuobjdump), "--list-text", str(binary)])
    symbols = listed_symbols(listing.stdout)
    selected: dict[str, str] = {}
    for requested, symbol_fragment in TARGET_FUNCTIONS.items():
        matches = sorted(
            symbol for symbol in set(symbols)
            if symbol_fragment in symbol
            and not (requested == "dependent_add_kernel" and "independent_add_kernel" in symbol)
        )
        if len(matches) != 1:
            raise RuntimeError(
                f"expected one sm_70 SASS function matching {symbol_fragment!r}, found {matches!r}"
            )
        selected[requested] = matches[0]

    binary_hash = binary_sha256(binary)
    report: dict[str, object] = {
        "binary": str(binary),
        "binary_sha256": binary_hash,
        "cuobjdump": str(cuobjdump),
        "cuobjdump_version": version.stdout.strip(),
        "architecture": "sm_70",
        "inspection": "offline SASS extraction only; no GPU execution or performance claim",
        "kernels": {},
    }
    kernel_reports: dict[str, object] = {}
    for requested, symbol in selected.items():
        sass, warnings = exact_sass(cuobjdump, binary, symbol)
        path = output_dir / f"{requested}.sm_70.sass"
        path.write_text(sass, encoding="utf-8")
        opcodes = {
            name: len(pattern.findall(sass))
            for name, pattern in OPCODE_PATTERNS.items()
        }
        kernel_reports[requested] = {
            "function_symbol": symbol,
            "sass_file": path.name,
            "sass_sha256": hashlib.sha256(sass.encode("utf-8")).hexdigest(),
            "opcode_occurrences": opcodes,
            "relevant_instruction_lines": [
                line.strip() for line in sass.splitlines()
                if RELEVANT_INSTRUCTION.search(line)
            ],
            "cuobjdump_warnings": warnings.strip(),
        }
    report["kernels"] = kernel_reports
    report_path = output_dir / "sass_report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path), "binary_sha256": binary_hash,
                      "kernels": list(kernel_reports)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(f"extract_atlas_sass: {error}", file=sys.stderr)
        raise SystemExit(2)
