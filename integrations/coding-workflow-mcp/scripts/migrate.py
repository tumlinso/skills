#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from coding_workflow_mcp.migration import MigrationError, migrate


def main() -> None:
    parser = argparse.ArgumentParser(description="Add or remove coding-workflow routing in AGENTS.md")
    parser.add_argument("--repo", required=True)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--dry-run", action="store_true")
    operation.add_argument("--apply", action="store_true")
    operation.add_argument("--remove", action="store_true")
    arguments = parser.parse_args()
    try:
        result = migrate(arguments.repo, apply=arguments.apply or arguments.remove, remove=arguments.remove)
    except MigrationError as error:
        result = {"status": "error", "reason": str(error)}
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        raise SystemExit(2) from None
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

