#!/usr/bin/env python3
"""Run implementation A and B under one comparison contract."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("compare_dir", type=Path)
    parser.add_argument("--impl-a-cmd", required=True, help="Shell command for implementation A wrapper")
    parser.add_argument("--impl-b-cmd", required=True, help="Shell command for implementation B wrapper")
    return parser.parse_args()


def run_one(cmd: str, out_dir: Path) -> int:
    completed = subprocess.run(
        ["bash", "-lc", cmd, "--", str(out_dir)],
        check=False,
    )
    return int(completed.returncode)


def main() -> int:
    args = parse_args()
    compare_dir = args.compare_dir
    impl_a_dir = compare_dir / "impl_a"
    impl_b_dir = compare_dir / "impl_b"
    impl_a_dir.mkdir(parents=True, exist_ok=True)
    impl_b_dir.mkdir(parents=True, exist_ok=True)

    a_status = run_one(args.impl_a_cmd, impl_a_dir)
    b_status = run_one(args.impl_b_cmd, impl_b_dir)

    combined = {"impl_a_exit_code": a_status, "impl_b_exit_code": b_status}
    (compare_dir / "run_status.json").write_text(json.dumps(combined, indent=2) + "\n")
    return 0 if a_status == 0 and b_status == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
