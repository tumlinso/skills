#!/usr/bin/env python3
"""Emit narrow nvcc gencode flags for architecture-specific tuning."""

from __future__ import annotations

import argparse
import json
import sys


FAMILY_FLAGS = {
    "volta": [("compute_70", "sm_70")],
    "ampere": [("compute_80", "sm_80")],
    "hopper": [("compute_90", "sm_90")],
    "blackwell": [("compute_100", "sm_100")],
}

SYSTEM_TO_FAMILY = {
    "native": "volta",
    "gb200-nvl72": "blackwell",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--family",
        choices=sorted(FAMILY_FLAGS) + ["mixed"],
        help="Architecture family to emit. Use mixed for a cross-family matrix.",
    )
    parser.add_argument(
        "--system",
        choices=sorted(SYSTEM_TO_FAMILY),
        help="System preset. Overridden by --family when both are given.",
    )
    parser.add_argument(
        "--format",
        choices=["shell", "json", "lines"],
        default="shell",
        help="Output format.",
    )
    parser.add_argument(
        "--embed-ptx",
        action="store_true",
        help="Also emit PTX for the newest architecture in the selected matrix.",
    )
    parser.add_argument(
        "--family-specific",
        action="store_true",
        help="Use Blackwell family-specific targets when the selected family is blackwell.",
    )
    return parser.parse_args()


def build_entries(family: str, family_specific: bool) -> list[tuple[str, str]]:
    if family == "mixed":
        entries: list[tuple[str, str]] = []
        for name in ("volta", "ampere", "hopper", "blackwell"):
            entries.extend(build_entries(name, family_specific))
        return entries
    entries = list(FAMILY_FLAGS[family])
    if family == "blackwell" and family_specific:
        return [("compute_100f", "sm_100f")]
    return entries


def emit_shell(entries: list[tuple[str, str]], embed_ptx: bool) -> str:
    flags = [f"-gencode arch={arch},code={code}" for arch, code in entries]
    if embed_ptx and entries:
        newest_arch = entries[-1][0]
        flags.append(f"-gencode arch={newest_arch},code={newest_arch}")
    return " ".join(flags)


def main() -> int:
    args = parse_args()
    family = args.family or SYSTEM_TO_FAMILY.get(args.system or "", "")
    if not family:
        raise SystemExit("Pass --family or --system.")
    entries = build_entries(family, args.family_specific)
    if args.format == "shell":
        print(emit_shell(entries, args.embed_ptx))
        return 0
    if args.format == "lines":
        for arch, code in entries:
            print(f"{arch} {code}")
        if args.embed_ptx and entries:
            newest_arch = entries[-1][0]
            print(f"{newest_arch} {newest_arch}")
        return 0
    payload = {
        "family": family,
        "family_specific": args.family_specific,
        "entries": [{"arch": arch, "code": code} for arch, code in entries],
        "embed_ptx": args.embed_ptx,
        "shell": emit_shell(entries, args.embed_ptx),
    }
    json.dump(payload, sys.stdout, indent=2)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
