"""Resource-aware gate execution with evidence capture and cleanup."""

from __future__ import annotations

import json
import os
import re
import subprocess
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .child_execution import authenticate_child_token, heartbeat_child_execution
from .config import utc_now
from .claims import pulse_claim
from .evidence import gate_input_fingerprint
from .graph import reevaluate_barriers
from .models import ExitCode, TodoError
from .ownership import acquire_named_locks, release_lock
from .projections import atomic_write_text
from .resources import acquire_resource, release_resource, resource_environment
from .sessions import authenticate_claim


def _child_candidate(conn, gate_id: str, fingerprint: str) -> dict[str, object] | None:
    """Return the newest successful, reported child candidate for current inputs."""
    rows = conn.execute(
        "SELECT e.* FROM evidence e WHERE e.gate_id=? AND e.status IN ('passed','evaluated_not_promoted') "
        "ORDER BY e.created_at DESC",
        (gate_id,),
    )
    for row in rows:
        try:
            metadata = json.loads(row["metadata_json"] or "{}")
        except json.JSONDecodeError:
            continue
        child_id = metadata.get("child_execution_id")
        if not child_id or metadata.get("input_fingerprint") != fingerprint:
            continue
        child = conn.execute("SELECT state,gates_json FROM child_executions WHERE id=?", (child_id,)).fetchone()
        if not child or child["state"] != "succeeded" or gate_id not in json.loads(child["gates_json"] or "[]"):
            continue
        accepted = False
        for acceptance in conn.execute("SELECT metadata_json FROM evidence WHERE gate_id=? ORDER BY created_at DESC", (gate_id,)):
            try:
                accepted_metadata = json.loads(acceptance["metadata_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if accepted_metadata.get("accepted_evidence_id") == row["id"]:
                accepted = True
                break
        if not accepted:
            return {"evidence": dict(row), "metadata": metadata, "child_execution_id": child_id}
    return None


def list_gates(conn, task_id: str | None = None) -> list[dict[str, object]]:
    if task_id:
        rows = conn.execute("SELECT * FROM gates WHERE task_id=? ORDER BY id", (task_id,))
    else:
        rows = conn.execute("SELECT * FROM gates ORDER BY id")
    result = []
    for row in rows:
        item = dict(row)
        item["config"] = json.loads(item.pop("config_json"))
        result.append(item)
    return result


def explain_gate(conn, gate_id: str) -> dict[str, object]:
    row = conn.execute("SELECT * FROM gates WHERE id=?", (gate_id,)).fetchone()
    if not row:
        raise TodoError("gate_not_found", f"Unknown gate {gate_id}")
    evidence = [dict(item) for item in conn.execute("SELECT * FROM evidence WHERE gate_id=? ORDER BY created_at DESC", (gate_id,))]
    item = dict(row)
    item["config"] = json.loads(item.pop("config_json"))
    item["evidence"] = evidence
    return item


def _json_value(value: object, path: str) -> object:
    current = value
    for part in path.split(".") if path else []:
        if isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _compare(actual: float, operator: str, expected: float) -> bool:
    return {
        ">=": actual >= expected,
        ">": actual > expected,
        "<=": actual <= expected,
        "<": actual < expected,
        "==": actual == expected,
    }.get(operator, False)


def _evaluate_static(repo_root: Path, gate_type: str, config: dict[str, object], conn) -> tuple[str, bool, dict[str, object]]:
    if gate_type == "file_exists":
        exists = (repo_root / str(config["path"])).exists()
        return ("passed" if exists else "failed", exists, {"path": config["path"], "exists": exists})
    if gate_type == "pattern":
        path = repo_root / str(config["path"])
        found = bool(path.is_file() and re.search(str(config["pattern"]), path.read_text(encoding="utf-8"), re.MULTILINE))
        return ("passed" if found else "failed", found, {"path": str(config["path"]), "found": found})
    if gate_type == "task_state":
        row = conn.execute("SELECT status,result FROM tasks WHERE id=?", (config["task_id"],)).fetchone()
        ok = bool(row and row["status"] == config.get("status", "done") and (not config.get("result") or row["result"] == config["result"]))
        return ("passed" if ok else "failed", ok, dict(row) if row else {})
    if gate_type == "checkpoint":
        row = conn.execute("SELECT state FROM checkpoints WHERE id=?", (config["checkpoint_id"],)).fetchone()
        ok = bool(row and row[0] == config.get("state", "reached"))
        return ("passed" if ok else "failed", ok, {"state": row[0] if row else "missing"})
    if gate_type == "interface":
        row = conn.execute("SELECT state,version,content_hash FROM interfaces WHERE id=?", (config["interface_id"],)).fetchone()
        ok = bool(row and row["state"] == config.get("state", "frozen") and (not config.get("version") or row["version"] == config["version"]))
        return ("passed" if ok else "failed", ok, dict(row) if row else {})
    if gate_type == "manual":
        ok = bool(config.get("accepted"))
        return ("passed" if ok else "failed", ok, {"accepted": ok, "note": config.get("note")})
    raise TodoError("unsupported_gate_type", f"Gate type {gate_type} is not executable")


def run_gate(db, paths, project: dict[str, object], gate_id: str, claim_token: str | None) -> tuple[dict[str, object], int]:
    configuration = project.get("configuration", {})
    resource_seconds = int(configuration.get("resource_lease_seconds", 300))
    claim_seconds = int(configuration.get("claim_lease_seconds", 7200))
    acquired: dict[str, object] = {}
    raw_tokens: dict[str, str] = {}

    def acquire(conn, revision):
        gate = conn.execute("SELECT * FROM gates WHERE id=?", (gate_id,)).fetchone()
        if not gate:
            raise TodoError("gate_not_found", f"Unknown gate {gate_id}")
        config = json.loads(gate["config_json"])
        child = None
        if gate["task_id"] and str(claim_token or "").startswith("toch_"):
            attempt = authenticate_child_token(conn, claim_token)
            execution = conn.execute(
                "SELECT id,gates_json FROM child_executions WHERE id=?",
                (attempt["child_execution_id"],),
            ).fetchone()
            allowed_gates = json.loads(execution["gates_json"] or "[]") if execution else []
            if gate_id not in allowed_gates:
                raise TodoError(
                    "child_gate_unauthorized",
                    f"Child execution is not authorized to run gate {gate_id}",
                    ExitCode.BLOCKED,
                    {"allowed_gates": allowed_gates},
                )
            if attempt["task_id"] != gate["task_id"]:
                raise TodoError("child_gate_task_mismatch", "Child gate does not belong to the parent task", ExitCode.INVALID_TOKEN)
            claim = conn.execute("SELECT * FROM claims WHERE id=?", (attempt["parent_claim_id"],)).fetchone()
            lease_seconds = max(resource_seconds, int(float(config.get("timeout", 3600))) + 30)
            heartbeat_child_execution(conn, claim_token, lease_seconds=lease_seconds)
            child = {
                "child_execution_id": attempt["child_execution_id"],
                "attempt_id": attempt["id"],
                "attempt_number": attempt["attempt_number"],
                "lease_seconds": lease_seconds,
            }
        else:
            if gate["task_id"]:
                pulse_claim(conn, claim_token, claim_seconds)
            claim = authenticate_claim(conn, claim_token) if gate["task_id"] else None
        if claim and claim["task_id"] != gate["task_id"]:
            raise TodoError("claim_task_mismatch", "Gate does not belong to the claimed task", ExitCode.INVALID_TOKEN)
        session_id = claim["session_id"] if claim else config.get("session_id")
        if not session_id:
            raise TodoError("gate_session_required", "Gate execution requires an active claim")
        fingerprint, inputs = gate_input_fingerprint(conn, paths.repo_root, config)
        accept_candidate = _child_candidate(conn, gate_id, fingerprint) if claim and not child else None
        resources = []
        selectors = sorted(str(item) for item in config.get("resources", []))
        argv = [str(item) for item in config.get("argv", [])]
        for selector in [] if accept_candidate else selectors:
            lease, token = acquire_resource(
                conn,
                selector=selector,
                session_id=session_id,
                claim_id=claim["id"] if claim else None,
                request_id=None,
                lease_seconds=resource_seconds,
                command=argv,
            )
            resources.append(lease)
            raw_tokens[f"resource:{lease['lease_id']}"] = token
        locks = acquire_named_locks(
            conn,
            [] if accept_candidate else [str(item) for item in config.get("locks", [])],
            claim_id=claim["id"] if claim else None,
            session_id=session_id,
            lease_seconds=resource_seconds,
            command=argv,
        )
        for lock in locks:
            raw_tokens[f"lock:{lock['lease_id']}"] = lock["token"]
        acquired.update(
            gate=dict(gate), config=config, claim=dict(claim) if claim else None, child=child,
            accept_candidate=accept_candidate, resources=resources, locks=locks,
            fingerprint=fingerprint, inputs=inputs,
        )
        return {"gate_id": gate_id, "resources": resources, "locks": [{k: v for k, v in item.items() if k != "token"} for item in locks]}

    _, acquire_revision = db.mutate(
        actor_session_id=None,
        entity_type="gate",
        entity_id=gate_id,
        event_type="gate.started",
        payload={"gate_id": gate_id},
        operation=acquire,
    )

    stop = threading.Event()

    def heartbeat() -> None:
        if stop.wait(max(1.0, resource_seconds / 3.0)):
            return
        while not stop.is_set():
            def refresh(conn, revision):
                del revision
                now = utc_now()
                expires = (datetime.now(timezone.utc) + timedelta(seconds=resource_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                for lease in acquired.get("resources", []):
                    conn.execute("UPDATE resource_leases SET heartbeat_at=?,expires_at=? WHERE id=? AND state='active'", (now, expires, lease["lease_id"]))
                for lease in acquired.get("locks", []):
                    conn.execute("UPDATE lock_leases SET heartbeat_at=?,expires_at=? WHERE id=? AND state='active'", (now, expires, lease["lease_id"]))
                child = acquired.get("child")
                if child:
                    child_expires = (datetime.now(timezone.utc) + timedelta(seconds=int(child["lease_seconds"]))).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                    conn.execute("UPDATE child_attempts SET heartbeat_at=?,expires_at=? WHERE id=? AND state='active'", (now, child_expires, child["attempt_id"]))
                    conn.execute("UPDATE child_executions SET heartbeat_at=? WHERE id=?", (now, child["child_execution_id"]))
                return True
            try:
                db.mutate(actor_session_id=None, entity_type="gate", entity_id=gate_id, event_type="gate.heartbeat", payload={}, operation=refresh)
            except Exception:
                pass
            stop.wait(max(1.0, resource_seconds / 3.0))

    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    gate = acquired["gate"]
    config = acquired["config"]
    gate_type = gate["type"]
    stdout = ""
    stderr = ""
    returncode: int | None = None
    status = "failed"
    valid = False
    details: dict[str, Any] = {}
    try:
        if acquired.get("accept_candidate"):
            candidate = acquired["accept_candidate"]
            status, valid = "passed", True
            details = {
                "accepted_child_evidence": True,
                "accepted_evidence_id": candidate["evidence"]["id"],
                "accepted_child_execution_id": candidate["child_execution_id"],
                "input_fingerprint": acquired["fingerprint"],
            }
        elif gate_type in {"command", "benchmark", "json_predicate"}:
            argv = config.get("argv")
            if not isinstance(argv, list) or not argv:
                raise TodoError("invalid_gate_command", "Command gates require a non-empty argv array")
            environment = os.environ.copy()
            environment.update({str(k): str(v) for k, v in config.get("env", {}).items()})
            environment.update(resource_environment(acquired["resources"]))
            result = subprocess.run(
                [str(item) for item in argv],
                cwd=paths.repo_root / str(config.get("cwd", ".")),
                env=environment,
                capture_output=True,
                text=True,
                timeout=float(config.get("timeout", 3600)),
                check=False,
            )
            stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
            expected = int(config.get("expected_exit_code", 0))
            executed = returncode == expected
            status = "passed" if executed else "failed"
            valid = executed
            details = {"argv": argv, "returncode": returncode, "expected_exit_code": expected, "environment": resource_environment(acquired["resources"])}
            if executed and gate_type in {"benchmark", "json_predicate"}:
                source: object
                metric_file = config.get("metric_file")
                source = json.loads((paths.repo_root / str(metric_file)).read_text(encoding="utf-8")) if metric_file else json.loads(stdout)
                actual = _json_value(source, str(config.get("metric_path", "")))
                passed = _compare(float(actual), str(config.get("operator", ">=")), float(config["threshold"]))
                details.update(actual=actual, threshold=config["threshold"], operator=config.get("operator", ">="))
                if passed:
                    status, valid = "passed", True
                elif gate_type == "benchmark" and bool(config.get("evaluation_required", True)):
                    status, valid = "evaluated_not_promoted", True
                else:
                    status, valid = "failed", False
        else:
            with db.read() as read_conn:
                status, valid, details = _evaluate_static(paths.repo_root, gate_type, config, read_conn)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        status, valid, details = "failed", False, {"timeout": config.get("timeout", 3600)}
    except KeyboardInterrupt:
        status, valid, details = "failed", False, {"interrupted": True}
    except Exception as exc:
        status, valid, details = "failed", False, {"error": str(exc)}
    finally:
        stop.set()
        thread.join(timeout=2)

    evidence_id = str(uuid.uuid4())
    evidence_dir = paths.evidence_dir / evidence_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(evidence_dir / "stdout.txt", stdout)
    atomic_write_text(evidence_dir / "stderr.txt", stderr)
    metadata = {
        **details,
        "input_fingerprint": acquired["fingerprint"],
        "inputs": acquired["inputs"],
        "resources": acquired["resources"],
        "locks": [{k: v for k, v in item.items() if k != "token"} for item in acquired["locks"]],
        "started_revision": acquire_revision,
    }
    if acquired.get("child"):
        metadata.update(acquired["child"])
        metadata["candidate_evidence"] = True

    def finish(conn, revision):
        for key, token in raw_tokens.items():
            if key.startswith("resource:"):
                release_resource(conn, token)
            else:
                release_lock(conn, token)
        if not acquired.get("child"):
            conn.execute(
                "UPDATE gates SET status=?,valid=?,input_fingerprint=?,last_run_at=?,revision=? WHERE id=?",
                (status, int(valid), acquired["fingerprint"], utc_now(), revision, gate_id),
            )
        evidence_kind = "child_gate_candidate" if acquired.get("child") else ("child_acceptance" if acquired.get("accept_candidate") else gate_type)
        conn.execute(
            "INSERT INTO evidence(id,gate_id,claim_id,kind,status,path,metadata_json,created_at,revision) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                evidence_id,
                gate_id,
                acquired["claim"]["id"] if acquired["claim"] else None,
                evidence_kind,
                status,
                str(evidence_dir),
                json.dumps(metadata, sort_keys=True),
                utc_now(),
                revision,
            ),
        )
        barriers = [] if acquired.get("child") else reevaluate_barriers(conn, revision)
        report = {
            "gate_id": gate_id,
            "task_id": gate["task_id"],
            "status": status,
            "valid": bool(valid),
            "evidence_id": evidence_id,
            "evidence_path": str(evidence_dir),
            "details": details,
            "barrier_changes": barriers,
        }
        if acquired.get("child"):
            report.update(candidate_valid=bool(valid), accepted=False)
        elif acquired.get("accept_candidate"):
            report["accepted"] = bool(valid)
        return report

    report, revision = db.mutate(
        actor_session_id=acquired["claim"]["session_id"] if acquired["claim"] else None,
        entity_type="gate",
        entity_id=gate_id,
        event_type="gate.completed",
        payload={"status": status, "valid": valid, "evidence_id": evidence_id},
        operation=finish,
    )
    return report, revision
