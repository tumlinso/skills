"""Checkpoint, barrier, interface, lock, resource, gate, guard, audit, and recovery commands."""

from __future__ import annotations

import subprocess
import time

from ..models import ExitCode, TodoError
from ..service import Service
from ..gates import run_gate


def _group(subparsers, helpers, name, actions):
    root = subparsers.add_parser(name)
    helpers.common(root)
    nested = root.add_subparsers(dest=f"{name}_action", required=True)
    return {action: nested.add_parser(action) for action in actions}


def register(subparsers, helpers) -> None:
    checkpoint = _group(subparsers, helpers, "checkpoint", ["reach", "revoke", "status"])
    for action, parser in checkpoint.items():
        helpers.common(parser)
        parser.add_argument("checkpoint_id")
        if action != "status":
            parser.add_argument("--claim-token", required=True)
        parser.set_defaults(handler=lambda args, value=action: Service(args.repo_root).checkpoint(value, args.checkpoint_id, getattr(args, "claim_token", None)))

    barrier = _group(subparsers, helpers, "barrier", ["status", "explain"])
    for action, parser in barrier.items():
        helpers.common(parser)
        parser.add_argument("barrier_id")
        parser.set_defaults(handler=lambda args: Service(args.repo_root).barrier(args.barrier_id))

    interface = _group(subparsers, helpers, "interface", ["freeze", "revise", "status"])
    for action, parser in interface.items():
        helpers.common(parser)
        parser.add_argument("interface_id")
        parser.add_argument("--version")
        if action != "status":
            parser.add_argument("--claim-token", required=True)
        parser.set_defaults(handler=lambda args, value=action: Service(args.repo_root).interface(value, args.interface_id, args.version, getattr(args, "claim_token", None)))

    decision = _group(subparsers, helpers, "decision", ["set", "status"])
    for action, parser in decision.items():
        helpers.common(parser)
        parser.add_argument("decision_id")
        if action == "set":
            parser.add_argument("value")
            parser.set_defaults(handler=lambda args: Service(args.repo_root).decision("set", args.decision_id, __import__("json").loads(args.value)))
        else:
            parser.set_defaults(handler=lambda args: Service(args.repo_root).decision("status", args.decision_id))

    locks = _group(subparsers, helpers, "lock", ["acquire", "release", "status"])
    for action, parser in locks.items():
        helpers.common(parser)
        if action == "acquire":
            parser.add_argument("name")
            parser.add_argument("--claim-token", required=True)
            parser.set_defaults(handler=lambda args: Service(args.repo_root).lock_acquire(args.name, args.claim_token))
        elif action == "release":
            parser.add_argument("--lease-token", required=True)
            parser.set_defaults(handler=lambda args: Service(args.repo_root).lock_release(args.lease_token))
        else:
            parser.add_argument("name", nargs="?")
            def lock_status(args):
                service = Service(args.repo_root)
                with service.db.read() as conn:
                    sql = "SELECT nl.name,nl.capacity,ll.id AS lease_id,ll.claim_id,ll.expires_at FROM named_locks nl LEFT JOIN lock_leases ll ON ll.lock_name=nl.name AND ll.state='active'"
                    params = ()
                    if args.name:
                        sql += " WHERE nl.name=?"
                        params = (args.name,)
                    return [dict(row) for row in conn.execute(sql + " ORDER BY nl.name", params)]
            parser.set_defaults(handler=lock_status)

    resource = _group(subparsers, helpers, "resource", ["discover", "list", "acquire", "release", "explain"])
    for action, parser in resource.items():
        helpers.common(parser)
        if action == "discover":
            parser.set_defaults(handler=lambda args: Service(args.repo_root).resource_discover())
        elif action == "list":
            parser.set_defaults(handler=lambda args: Service(args.repo_root).resource_list())
        elif action == "acquire":
            parser.add_argument("selector")
            parser.add_argument("--claim-token", required=True)
            parser.add_argument("--wait", type=float, default=0.0, metavar="SECONDS")
            def acquire_resource_with_wait(args):
                deadline = time.monotonic() + max(0.0, args.wait)
                while True:
                    try:
                        return Service(args.repo_root).resource_acquire(args.selector, args.claim_token)
                    except TodoError as exc:
                        if exc.code != "resource_unavailable" or time.monotonic() >= deadline:
                            raise
                        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))
            parser.set_defaults(handler=acquire_resource_with_wait)
        elif action == "release":
            parser.add_argument("--lease-token", required=True)
            parser.set_defaults(handler=lambda args: Service(args.repo_root).resource_release(args.lease_token))
        else:
            parser.add_argument("selector")
            parser.set_defaults(handler=lambda args: {"selector": args.selector, "resources": [item for item in Service(args.repo_root).resource_list() if (args.selector.endswith(":any") and item["class_id"] == args.selector[:-4]) or item["id"] == args.selector]})

    gate = _group(subparsers, helpers, "gate", ["list", "run", "explain"])
    helpers.common(gate["list"])
    gate["list"].add_argument("--task-id")
    gate["list"].set_defaults(handler=lambda args: Service(args.repo_root).gate_list(args.task_id))
    helpers.common(gate["explain"])
    gate["explain"].add_argument("gate_id")
    gate["explain"].set_defaults(handler=lambda args: Service(args.repo_root).gate_explain(args.gate_id))
    helpers.common(gate["run"])
    gate["run"].add_argument("gate_id", nargs="?")
    gate["run"].add_argument("--claim-token", required=True)
    gate["run"].add_argument("--required", action="store_true")
    gate["run"].add_argument("--accept-child")
    def run_gates(args):
        service = Service(args.repo_root)
        def run_one(gate_id):
            result, revision = run_gate(
                service.db, service.paths, service.project, gate_id, args.claim_token,
                accept_child=args.accept_child,
            )
            result["project_revision"] = revision
            result["projection"] = service.refresh({str(result["task_id"])})
            return result
        if args.required:
            if args.accept_child:
                raise TodoError("accept_child_requires_gate", "--accept-child requires one explicit gate ID")
            with service.db.read() as conn:
                from ..sessions import authenticate_claim
                claim = authenticate_claim(conn, args.claim_token)
                ids = [row[0] for row in conn.execute("SELECT id FROM gates WHERE task_id=? AND required=1 ORDER BY id", (claim["task_id"],))]
            results = [run_one(gate_id) for gate_id in ids]
            failed = [item for item in results if not item["valid"]]
            if failed:
                raise TodoError("gate_failed", "One or more required gates failed", ExitCode.GATE_FAILURE, {"results": results, "failed": failed})
            return {"results": results}
        if not args.gate_id:
            raise TodoError("gate_id_required", "gate run requires a gate ID or --required")
        result = run_one(args.gate_id)
        if not result["valid"]:
            raise TodoError("gate_failed", f"Gate {args.gate_id} failed", ExitCode.GATE_FAILURE, result)
        return result
    gate["run"].set_defaults(handler=run_gates)

    guard = subparsers.add_parser("guard")
    helpers.common(guard)
    guard.add_argument("--claim-token", required=True)
    guard.add_argument("--paths", nargs="+", required=True)
    guard.set_defaults(handler=lambda args: Service(args.repo_root).guard(args.claim_token, args.paths))

    for name in ("audit", "reconcile"):
        parser = subparsers.add_parser(name)
        helpers.common(parser)
        parser.set_defaults(handler=lambda args, method=name: getattr(Service(args.repo_root), method)())

    recover = _group(subparsers, helpers, "recover", ["inspect", "release", "adopt"])
    for action, parser in recover.items():
        helpers.common(parser)
        parser.add_argument("task_id")
        parser.add_argument("--session-token")
        parser.add_argument("--acknowledge-dirty", action="store_true")
        parser.set_defaults(handler=lambda args, value=action: Service(args.repo_root).recover(value, args.task_id, session_token=args.session_token, acknowledge_dirty=args.acknowledge_dirty))

    execute = subparsers.add_parser("exec")
    helpers.common(execute)
    execute.add_argument("--lock", action="append", default=[])
    execute.add_argument("--claim-token", required=True)
    execute.add_argument("command", nargs="+")
    def exec_locked(args):
        service = Service(args.repo_root)
        leases = service.lock_acquire_many(sorted(set(args.lock)), args.claim_token, args.command)["leases"]
        try:
            result = subprocess.run(args.command, cwd=service.paths.repo_root, check=False)
            if result.returncode:
                raise TodoError("exec_failed", f"Wrapped command exited with {result.returncode}", ExitCode.GATE_FAILURE, {"returncode": result.returncode})
            return {"returncode": result.returncode, "locks": [item["name"] for item in leases]}
        finally:
            for lease in reversed(leases):
                service.lock_release(lease["token"])
    execute.set_defaults(handler=exec_locked)
