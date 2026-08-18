#!/usr/bin/env python3
"""Report whether a CUDA translation unit contains more than one kernel."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


KERNEL_RE = re.compile(r"__global__\s+(?:\w+\s+)*([A-Za-z_]\w*)\s*\(")


def scan(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    kernels = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = KERNEL_RE.search(line)
        if match:
            kernels.append({"name": match.group(1), "line": lineno})
    return {
        "path": str(path),
        "kernel_count": len(kernels),
        "single_kernel_ok": len(kernels) <= 1,
        "kernels": kernels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", help="CUDA translation units to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args()

    payload = [scan(Path(raw).resolve()) for raw in args.paths]
    if args.json:
        json.dump(payload if len(payload) > 1 else payload[0], sys.stdout, indent=2)
        print()
        return 0

    for item in payload:
        print(f"path={item['path']}")
        print(f"kernel_count={item['kernel_count']}")
        print(f"single_kernel_ok={str(item['single_kernel_ok']).lower()}")
        for kernel in item["kernels"]:
            print(f"kernel={kernel['name']} line={kernel['line']}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
