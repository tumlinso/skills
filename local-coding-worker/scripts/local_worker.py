#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from worker_core import WorkerError, eligibility, run_controller


def _request(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded CORE4 local coding worker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("eligible", "run"):
        command = subparsers.add_parser(name)
        command.add_argument("--request", required=True, help="LCW-REQUEST/1 JSON path or - for stdin")
    args = parser.parse_args()
    try:
        request = _request(args.request)
        result = eligibility(request) if args.command == "eligible" else run_controller(request)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0 if result.get("eligible", True) else 2
    except (OSError, json.JSONDecodeError, WorkerError) as error:
        print(json.dumps({"format": "LOCAL-CODING-WORKER-ERROR/1", "error": str(error)}, sort_keys=True,
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
