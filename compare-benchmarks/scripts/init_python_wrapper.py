#!/usr/bin/env python3
"""Emit a simple Python wrapper template for one implementation."""

from __future__ import annotations

import argparse
from pathlib import Path


TEMPLATE = """#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "run_config.json").write_text(json.dumps({{"implementation": "{name}"}}, indent=2) + "\\n")
    (out_dir / "results.json").write_text(
        json.dumps({{"phases": [], "metrics": {{}}, "checks": {{"valid": False}}}}, indent=2) + "\\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
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
