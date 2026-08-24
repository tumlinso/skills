#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tomllib
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
from local_worker.model_cache import ModelCache, ModelCacheError  # noqa: E402
from local_worker.supervisor import SupervisorClient, SupervisorError  # noqa: E402
from local_worker.production_checks import (ProductionCheckError, evaluate, host_check,
                                            release_check, validate_policy)  # noqa: E402
from local_worker.verification import VerificationError  # noqa: E402
from local_worker.workspace import WorkspaceError  # noqa: E402


def _request(path: str) -> object:
    if path == "-":
        return json.load(sys.stdin)
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _model_cache() -> ModelCache:
    profile = tomllib.loads((SKILL_ROOT / "config/production-profile.toml").read_text(encoding="utf-8"))
    storage = profile["storage"]
    return ModelCache(storage["cache_root"], storage["canonical_root"])


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded CORE4 local coding worker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("eligible", "run"):
        command = subparsers.add_parser(name)
        command.add_argument("--request", required=True, help="LCW-REQUEST/1 JSON path or - for stdin")
    integrate = subparsers.add_parser("integrate")
    integrate.add_argument("--request", required=True, help="CORE4-INTEGRATION-REQUEST/1 JSON path or -")
    delegate = subparsers.add_parser("delegate")
    delegate.add_argument("--claim-token", required=True)
    delegate.add_argument("--mode", required=True, choices=["readonly", "writable"])
    delegate.add_argument("--target")
    delegate.add_argument("--wait", action="store_true")
    delegate.add_argument("--json", action="store_true")
    self_test = subparsers.add_parser("self-test")
    self_test.add_argument("--repo", default=".")
    self_test.add_argument("--json", action="store_true")
    model_cache = subparsers.add_parser("model-cache")
    cache_commands = model_cache.add_subparsers(dest="cache_command", required=True)
    for name in ("inspect", "list", "install", "verify", "activate", "remove"):
        command = cache_commands.add_parser(name)
        command.add_argument("--json", action="store_true")
    cache_commands.choices["install"].add_argument("--candidate-id", required=True)
    cache_commands.choices["install"].add_argument("--activate", action="store_true")
    for name in ("verify", "activate", "remove"):
        cache_commands.choices[name].add_argument("--candidate-id")
        cache_commands.choices[name].add_argument("--payload-sha256")
    cache_commands.choices["verify"].add_argument("--quick", action="store_true")
    cache_commands.choices["verify"].add_argument("--full", action="store_true")
    host = subparsers.add_parser("host-check")
    host.add_argument("--scenario", required=True, choices=["service", "readonly", "writable"])
    host.add_argument("--json", action="store_true")
    service = subparsers.add_parser("service")
    service.add_argument("--repo-root", default=".")
    service_commands = service.add_subparsers(dest="service_command", required=True)
    for name in ("status", "warm", "drain", "evict", "stop"):
        service_commands.add_parser(name).add_argument("--json", action="store_true")
    evaluation = subparsers.add_parser("evaluate")
    evaluation.add_argument("--phase", required=True, choices=["focused", "meaningful"])
    evaluation.add_argument("--json", action="store_true")
    policy = subparsers.add_parser("policy")
    policy_subcommands = policy.add_subparsers(dest="policy_command", required=True)
    policy_subcommands.add_parser("validate").add_argument("--json", action="store_true")
    release = subparsers.add_parser("release-check")
    release.add_argument("--phase", required=True, choices=["cleanup", "integrated", "release", "handoff"])
    release.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "service":
            result = SupervisorClient(args.repo_root).request(args.service_command)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "host-check":
            print(json.dumps(host_check(args.scenario), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "evaluate":
            print(json.dumps(evaluate(args.phase), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "policy":
            print(json.dumps(validate_policy(), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "release-check":
            print(json.dumps(release_check(args.phase), ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
        if args.command == "model-cache":
            cache = _model_cache()
            if args.cache_command == "inspect":
                result = cache.inspect()
            elif args.cache_command == "list":
                result = {"format": "CORE4-MODEL-CACHE-LIST/1", "entries": cache.list()}
            elif args.cache_command == "install":
                result = cache.install(args.candidate_id, activate=args.activate)
            else:
                active = cache.active() or {}
                candidate_id = args.candidate_id or active.get("candidate_id")
                payload_sha256 = args.payload_sha256 or active.get("payload_sha256")
                if not candidate_id or not payload_sha256:
                    raise ModelCacheError("candidate and payload hash are required when no active profile exists")
                if args.cache_command == "verify":
                    if args.quick and args.full:
                        raise ModelCacheError("choose only one of --quick or --full")
                    result = cache.verify(candidate_id, payload_sha256, full=bool(args.full))
                elif args.cache_command == "activate":
                    result = cache.activate(candidate_id, payload_sha256)
                else:
                    result = cache.remove(candidate_id, payload_sha256)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
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
        if args.command == "delegate":
            result = IntegrationController().delegate(Path.cwd(), args.claim_token, mode=args.mode, target=args.target)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
            return 0
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
            AcceptanceError, VerificationError, WorkspaceError, ModelCacheError,
            ProductionCheckError, SupervisorError) as error:
        print(json.dumps({"format": "LOCAL-CODING-WORKER-ERROR/1", "error": str(error)}, sort_keys=True,
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
