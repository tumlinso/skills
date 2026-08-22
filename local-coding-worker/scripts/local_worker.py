#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from worker_core import WorkerError, eligibility, run_controller

SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = Path(__file__).resolve().parent
while str(SCRIPT_ROOT) in sys.path:
    sys.path.remove(str(SCRIPT_ROOT))
if str(SKILL_ROOT) in sys.path:
    sys.path.remove(str(SKILL_ROOT))
sys.path.insert(0, str(SKILL_ROOT))

from local_worker.acceptance import AcceptanceError  # noqa: E402
from local_worker.controller import IntegrationController, IntegrationError  # noqa: E402
from local_worker.verification import VerificationError  # noqa: E402
from local_worker.workspace import WorkspaceError  # noqa: E402


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
    integrate = subparsers.add_parser("integrate")
    integrate.add_argument("--request", required=True, help="CORE4-INTEGRATION-REQUEST/1 JSON path or -")
    self_test = subparsers.add_parser("self-test")
    self_test.add_argument("--repo", default=".")
    self_test.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "self-test":
            root = Path(args.repo).resolve()
            process = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "local-coding-worker/tests",
                 "-p", "test_core4_integration.py", "-v"],
                cwd=root, text=True, capture_output=True, check=False,
            )
            result = {
                "format": "CORE4-INTEGRATION-SELF-TEST/1",
                "schema_version": 1,
                "ok": process.returncode == 0,
                "scenarios": [
                    "readonly", "writable", "needs_codex", "stale_patch",
                    "preemption", "accepted_patch", "cuda_trigger",
                ],
                "tests_run": sum(1 for line in process.stderr.splitlines() if line.startswith("test_")),
            }
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0 if result["ok"] else 2
        request = _request(args.request)
        if args.command == "eligible":
            result = eligibility(request)
        elif args.command == "run":
            result = run_controller(request)
        else:
            result = IntegrationController().run(request)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
        return 0 if result.get("eligible", True) else 2
    except (OSError, json.JSONDecodeError, WorkerError, IntegrationError,
            AcceptanceError, VerificationError, WorkspaceError) as error:
        print(json.dumps({"format": "LOCAL-CODING-WORKER-ERROR/1", "error": str(error)}, sort_keys=True,
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
