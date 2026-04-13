#!/usr/bin/env python3
"""Emit a simple CLI wrapper template for one implementation."""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

# Fill in the real command for this implementation.
# Required outputs:
# - run_config.json
# - results.json

OUT_DIR="${1:?output dir required}"
mkdir -p "${OUT_DIR}"
printf '{\\n  "implementation": "%s"\\n}\\n' "{name}" > "${OUT_DIR}/run_config.json"
printf '{\\n  "phases": [],\\n  "metrics": {},\\n  "checks": {{"valid": false}}\\n}\\n' > "${OUT_DIR}/results.json"
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--name", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.path.write_text(TEMPLATE.format(name=args.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
