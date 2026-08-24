#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import tomllib
import uuid
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
from local_worker.supervisor import SupervisorClient, SupervisorError, runtime_root  # noqa: E402
from local_worker.production_checks import (ProductionCheckError, evaluate, host_check,
                                            release_check, validate_policy)  # noqa: E402
from local_worker.service import AdapterError  # noqa: E402
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


def _delegation_root() -> Path:
    root = runtime_root() / "delegations"
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    root.chmod(0o700)
    return root


def _atomic_json(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, path)


def _execution_path(execution_id: str, suffix: str) -> Path:
    try:
        normalized = str(uuid.UUID(execution_id))
    except ValueError as error:
        raise IntegrationError("invalid delegation execution id") from error
    return _delegation_root() / f"{normalized}.{suffix}"


def _launch_delegate(repo: Path, claim_token: str, mode: str, target: str | None) -> dict[str, object]:
    execution_id = str(uuid.uuid4())
    request_path = _execution_path(execution_id, "request.json")
    _atomic_json(request_path, {
        "execution_id": execution_id, "repo_root": str(repo.resolve()),
        "claim_token": claim_token, "mode": mode, "target": target,
    })
    log_path = _execution_path(execution_id, "log")
    with log_path.open("ab") as log:
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).resolve()), "_delegate-worker", "--request", str(request_path)],
            cwd=repo, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
        )
    _atomic_json(_execution_path(execution_id, "launch.json"), {"pid": process.pid})
    return {"format": "CORE4-DELEGATE-LAUNCH/1", "execution_id": execution_id,
            "pid": process.pid, "state": "running"}


def _run_detached_delegate(request_path: Path) -> int:
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        request_path.unlink(missing_ok=True)
        execution_id = str(request["execution_id"])
        result = IntegrationController().delegate(
            Path(str(request["repo_root"])), str(request["claim_token"]),
            mode=str(request["mode"]), target=request.get("target"),
        )
        state = "completed"
        payload: dict[str, object] = {"result": result}
    except Exception as error:  # The detached boundary must always leave a collectable result.
        execution_id = str(locals().get("request", {}).get("execution_id", request_path.name.split(".", 1)[0]))
        state = "failed"
        payload = {"error": str(error)}
    _atomic_json(_execution_path(execution_id, "result.json"), {
        "format": "CORE4-DELEGATE-COLLECT/1", "execution_id": execution_id,
        "state": state, **payload,
    })
    return 0 if state == "completed" else 2


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _collect_delegate(execution_id: str, *, wait: bool, timeout: float) -> dict[str, object]:
    result_path = _execution_path(execution_id, "result.json")
    launch_path = _execution_path(execution_id, "launch.json")
    if not launch_path.is_file() and not result_path.is_file():
        raise IntegrationError("unknown delegation execution id")
    deadline = time.monotonic() + timeout
    while wait and not result_path.is_file() and time.monotonic() < deadline:
        time.sleep(0.1)
    if result_path.is_file():
        value = json.loads(result_path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise IntegrationError("delegation result is invalid")
        return value
    launch = json.loads(launch_path.read_text(encoding="utf-8"))
    pid = int(launch["pid"])
    state = "running" if _pid_alive(pid) else "failed"
    result: dict[str, object] = {"format": "CORE4-DELEGATE-COLLECT/1",
        "execution_id": execution_id, "state": state, "pid": pid}
    if state == "failed":
        result["error"] = "delegate process exited without a result"
    elif wait:
        result["retryable"] = True
        result["reason"] = "collection timeout"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded CORE4 local coding worker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("eligible", "run"):
        command = subparsers.add_parser(name)
        command.add_argument("--request", required=True, help="LCW-REQUEST/1 JSON path or - for stdin")
    integrate = subparsers.add_parser("integrate")
    integrate.add_argument("--request", required=True, help="CORE4-INTEGRATION-REQUEST/1 JSON path or -")
    delegate = subparsers.add_parser("delegate")
    delegate.add_argument("--claim-token")
    delegate.add_argument("--mode", choices=["readonly", "writable"])
    delegate.add_argument("--target")
    delegate.add_argument("--collect", metavar="EXECUTION_ID")
    delegate.add_argument("--wait", action="store_true")
    delegate.add_argument("--timeout", type=float, default=900.0)
    delegate.add_argument("--json", action="store_true")
    detached = subparsers.add_parser("_delegate-worker", help=argparse.SUPPRESS)
    detached.add_argument("--request", required=True)
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
    host.add_argument("--scenario", required=True,
                      choices=["service", "structured-output", "readonly", "writable"])
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
        if args.command == "_delegate-worker":
            return _run_detached_delegate(Path(args.request))
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
            if args.collect:
                if args.claim_token or args.mode or args.target:
                    raise IntegrationError("--collect cannot be combined with launch arguments")
                result = _collect_delegate(args.collect, wait=args.wait, timeout=args.timeout)
                print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
                return 0 if result.get("state") != "failed" else 2
            if not args.claim_token or not args.mode:
                raise IntegrationError("delegate launch requires --claim-token and --mode")
            if args.wait:
                result = IntegrationController().delegate(Path.cwd(), args.claim_token, mode=args.mode,
                                                          target=args.target)
            else:
                result = _launch_delegate(Path.cwd(), args.claim_token, args.mode, args.target)
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
    except (OSError, json.JSONDecodeError, WorkerError, IntegrationError, AdapterError,
            AcceptanceError, VerificationError, WorkspaceError, ModelCacheError,
            ProductionCheckError, SupervisorError) as error:
        print(json.dumps({"format": "LOCAL-CODING-WORKER-ERROR/1", "error": str(error)}, sort_keys=True,
                         separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
