#!/usr/bin/env python3
"""Emit a narrow Volta profile-build command fragment."""

from __future__ import annotations

import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fast-math", action="store_true", help="Include --use_fast_math.")
    parser.add_argument("--debug", action="store_true", help="Emit an sm_70 debug build instead of a profile build.")
    args = parser.parse_args()

    if args.debug:
        print("-O0 -g -G -std=c++17 -arch=sm_70 -lineinfo -Xcompiler=-fno-omit-frame-pointer")
        return 0

    parts = [
        "-O3",
        "-std=c++17",
        "-arch=sm_70",
        "-lineinfo",
        "-Xptxas=-v",
        "-Xcompiler=-fno-omit-frame-pointer",
        "-DNDEBUG",
    ]
    if args.fast_math:
        parts.append("--use_fast_math")
    print(" ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
