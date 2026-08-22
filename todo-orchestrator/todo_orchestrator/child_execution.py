"""Restricted child executions subordinate to an active todo claim.

Child executions deliberately are not tasks.  Their credentials authorize only
the heartbeat and result operations in this module; parent task lifecycle and
acceptance remain guarded by the ordinary claim token.
"""

from __future__ import annotations

import json
import posixpath
import secrets
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import utc_now
from .git_state import canonical_relative, paths_overlap
from .models import ExitCode, TodoError
from .ownership import scopes_for
from .sessions import authenticate_claim, token_hash

TERMINAL_STATES = {"succeeded", "failed", "needs_codex", "canceled"}
RESULT_STATES = {"succeeded", "failed", "needs_codex"}


def _iso_after(seconds: int) -> str:
    if seconds <= 0:
        raise TodoError("invalid_child_lease", "Child lease duration must be positive")
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root + "/")


def _relative_path(value: str) -> str:
    normalized = posixpath.normpath(value.strip().replace("\\", "/"))
    if not value.strip() or normalized in {".", ".."} or normalized.startswith("../") or normalized.startswith("/"):
        raise TodoError("invalid_child_path", f"Child path must be repository-relative: {value!r}")
    return normalized


def _execution(conn: sqlite3.Connection, child_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM child_executions WHERE id=?", (child_id,)).fetchone()
    if not row:
        raise TodoError("unknown_child_execution", f"Child execution {child_id} does not exist", ExitCode.BLOCKED)
    return row


def _parent_claim(conn: sqlite3.Connection, claim_token: str, child_id: str | None = None) -> sqlite3.Row:
    claim = authenticate_claim(conn, claim_token)
    if child_id:
        child = _execution(conn, child_id)
        if child["parent_claim_id"] != claim["id"]:
            raise TodoError("child_parent_mismatch", "Child execution is not owned by this claim", ExitCode.INVALID_TOKEN)
    return claim


def _release_scopes(conn: sqlite3.Connection, child_id: str, now: str) -> None:
    conn.execute(
        "UPDATE child_scope_leases SET state='released',released_at=? WHERE child_execution_id=? AND state='active'",
        (now, child_id),
    )


def _start_attempt(conn: sqlite3.Connection, child_id: str, lease_seconds: int) -> tuple[dict[str, object], str]:
    child = _execution(conn, child_id)
    attempt_number = int(child["attempt_count"]) + 1
    if attempt_number > int(child["max_attempts"]):
        raise TodoError("child_attempts_exhausted", "Child execution has no attempts remaining", ExitCode.BLOCKED)
    now = utc_now()
    expires_at = _iso_after(lease_seconds)
    attempt_id = str(uuid.uuid4())
    raw_token = "toch_" + secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO child_attempts(id,child_execution_id,attempt_number,token_hash,state,created_at,heartbeat_at,expires_at) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (attempt_id, child_id, attempt_number, token_hash(raw_token), "active", now, now, expires_at),
    )
    conn.execute(
        "UPDATE child_executions SET state='running',attempt_count=?,started_at=COALESCE(started_at,?),heartbeat_at=? WHERE id=?",
        (attempt_number, now, now, child_id),
    )
    return {
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "expires_at": expires_at,
    }, raw_token


def sweep_expired_child_executions(conn: sqlite3.Connection) -> list[str]:
    """Move stale active attempts into an explicit parent-recovery state."""
    now = utc_now()
    stale = conn.execute(
        "SELECT a.id,a.child_execution_id,c.cancel_requested,p.state AS parent_state,p.expires_at AS parent_expires_at "
        "FROM child_attempts a JOIN child_executions c ON c.id=a.child_execution_id "
        "JOIN claims p ON p.id=c.parent_claim_id "
        "WHERE a.state='active' AND (a.expires_at<=? OR p.state<>'active' OR p.expires_at<=?) ORDER BY a.expires_at",
        (now, now),
    ).fetchall()
    changed: list[str] = []
    for row in stale:
        conn.execute("UPDATE child_attempts SET state='expired',completed_at=? WHERE id=?", (now, row["id"]))
        parent_inactive = row["parent_state"] != "active" or row["parent_expires_at"] <= now
        state = "canceled" if row["cancel_requested"] or parent_inactive else "recovery_required"
        conn.execute(
            "UPDATE child_executions SET state=?,completed_at=CASE WHEN ?='canceled' THEN ? ELSE NULL END WHERE id=?",
            (state, state, now, row["child_execution_id"]),
        )
        if state == "canceled":
            _release_scopes(conn, row["child_execution_id"], now)
        changed.append(str(row["child_execution_id"]))
    return changed


def authorize_child_execution(
    conn: sqlite3.Connection,
    repo_root: Path,
    claim_token: str,
    *,
    objective: str,
    scopes: list[str],
    gates: list[str] | None = None,
    max_attempts: int = 1,
    lease_seconds: int = 300,
) -> dict[str, object]:
    """Authorize one bounded child and return its first restricted token."""
    claim = authenticate_claim(conn, claim_token)
    objective = objective.strip()
    if not objective:
        raise TodoError("invalid_child_objective", "Child objective must not be empty")
    if max_attempts < 1:
        raise TodoError("invalid_child_attempts", "max_attempts must be at least one")
    parent_scopes = scopes_for(conn, claim["task_id"], "exclusive")
    normalized = sorted({canonical_relative(repo_root, value) for value in scopes})
    if not normalized:
        raise TodoError("invalid_child_scope", "At least one child scope is required")
    denied = [path for path in normalized if not any(_inside(path, root) for root in parent_scopes)]
    if denied:
        raise TodoError(
            "child_scope_violation",
            "Child scopes must be subsets of the parent claim's exclusive scope",
            ExitCode.BLOCKED,
            {"denied": denied, "parent_scopes": parent_scopes},
        )
    sweep_expired_child_executions(conn)
    for lease in conn.execute("SELECT child_execution_id,path FROM child_scope_leases WHERE state='active'"):
        if any(paths_overlap(path, lease["path"]) for path in normalized):
            raise TodoError(
                "child_scope_unavailable",
                "A requested child scope is already leased",
                ExitCode.CONTENTION,
                {"child_execution_id": lease["child_execution_id"], "path": lease["path"]},
            )
    now = utc_now()
    child_id = str(uuid.uuid4())
    unique_gates = sorted({value.strip() for value in gates or [] if value.strip()})
    conn.execute(
        "INSERT INTO child_executions(id,parent_claim_id,task_id,objective,gates_json,state,max_attempts,created_at) "
        "VALUES(?,?,?,?,?,'authorized',?,?)",
        (child_id, claim["id"], claim["task_id"], objective, json.dumps(unique_gates), max_attempts, now),
    )
    for path in normalized:
        conn.execute(
            "INSERT INTO child_scope_leases(child_execution_id,path,state,acquired_at) VALUES(?,?,'active',?)",
            (child_id, path, now),
        )
    attempt, raw_token = _start_attempt(conn, child_id, lease_seconds)
    return {
        "child_execution_id": child_id,
        "task_id": claim["task_id"],
        "state": "running",
        "objective": objective,
        "scopes": normalized,
        "gates": unique_gates,
        "max_attempts": max_attempts,
        "attempt": attempt,
        "child_token": raw_token,
    }


def authenticate_child_token(conn: sqlite3.Connection, child_token: str | None) -> sqlite3.Row:
    if not child_token:
        raise TodoError("invalid_child_token", "A child token is required", ExitCode.INVALID_TOKEN)
    row = conn.execute(
        "SELECT a.*,c.task_id,c.parent_claim_id,c.state AS execution_state,c.cancel_requested,"
        "p.state AS parent_claim_state,p.expires_at AS parent_expires_at "
        "FROM child_attempts a JOIN child_executions c ON c.id=a.child_execution_id "
        "JOIN claims p ON p.id=c.parent_claim_id "
        "WHERE a.token_hash=? AND a.state='active'",
        (token_hash(child_token),),
    ).fetchone()
    if not row:
        raise TodoError("invalid_child_token", "Child token is invalid or inactive", ExitCode.INVALID_TOKEN)
    if row["expires_at"] <= utc_now():
        raise TodoError("expired_child_token", "Child token expired and requires parent recovery", ExitCode.INVALID_TOKEN)
    if row["parent_claim_state"] != "active" or row["parent_expires_at"] <= utc_now():
        raise TodoError("inactive_child_parent", "Parent claim is no longer active", ExitCode.INVALID_TOKEN)
    if row["cancel_requested"] or row["execution_state"] != "running":
        raise TodoError("invalid_child_token", "Child execution is not active", ExitCode.INVALID_TOKEN)
    return row


def heartbeat_child_execution(conn: sqlite3.Connection, child_token: str, *, lease_seconds: int = 300) -> dict[str, object]:
    attempt = authenticate_child_token(conn, child_token)
    now = utc_now()
    expires_at = _iso_after(lease_seconds)
    conn.execute("UPDATE child_attempts SET heartbeat_at=?,expires_at=? WHERE id=?", (now, expires_at, attempt["id"]))
    conn.execute("UPDATE child_executions SET heartbeat_at=? WHERE id=?", (now, attempt["child_execution_id"]))
    return {
        "child_execution_id": attempt["child_execution_id"],
        "task_id": attempt["task_id"],
        "attempt_number": attempt["attempt_number"],
        "state": "running",
        "expires_at": expires_at,
    }


def report_child_result(
    conn: sqlite3.Connection,
    child_token: str,
    *,
    status: str,
    summary: str = "",
    changed_paths: list[str] | None = None,
) -> dict[str, object]:
    attempt = authenticate_child_token(conn, child_token)
    if status not in RESULT_STATES:
        raise TodoError("invalid_child_result", f"Child result status must be one of {sorted(RESULT_STATES)}")
    child_id = str(attempt["child_execution_id"])
    leased = [row[0] for row in conn.execute("SELECT path FROM child_scope_leases WHERE child_execution_id=?", (child_id,))]
    changed = sorted({_relative_path(path) for path in changed_paths or []})
    denied = [path for path in changed if not any(_inside(path, root) for root in leased)]
    if denied:
        raise TodoError("child_result_scope_violation", "Child reported paths outside its lease", ExitCode.BLOCKED, {"denied": denied})
    now = utc_now()
    result = {"status": status, "summary": summary, "changed_paths": changed}
    conn.execute(
        "UPDATE child_attempts SET state=?,completed_at=?,result_json=? WHERE id=?",
        (status, now, json.dumps(result, sort_keys=True), attempt["id"]),
    )
    child = _execution(conn, child_id)
    execution_state = status
    if status == "failed" and int(child["attempt_count"]) < int(child["max_attempts"]):
        execution_state = "recovery_required"
    completed_at = None if execution_state == "recovery_required" else now
    conn.execute(
        "UPDATE child_executions SET state=?,result_json=?,completed_at=? WHERE id=?",
        (execution_state, json.dumps(result, sort_keys=True), completed_at, child_id),
    )
    if execution_state in TERMINAL_STATES:
        _release_scopes(conn, child_id, now)
    return {
        "child_execution_id": child_id,
        "task_id": attempt["task_id"],
        "attempt_number": attempt["attempt_number"],
        "state": execution_state,
        "result": result,
        "parent_task_completed": False,
    }


def cancel_child_execution(conn: sqlite3.Connection, claim_token: str, child_id: str) -> dict[str, object]:
    claim = _parent_claim(conn, claim_token, child_id)
    child = _execution(conn, child_id)
    if child["state"] in TERMINAL_STATES:
        return {"child_execution_id": child_id, "task_id": claim["task_id"], "state": child["state"]}
    now = utc_now()
    conn.execute("UPDATE child_attempts SET state='canceled',completed_at=? WHERE child_execution_id=? AND state='active'", (now, child_id))
    conn.execute("UPDATE child_executions SET state='canceled',cancel_requested=1,completed_at=? WHERE id=?", (now, child_id))
    _release_scopes(conn, child_id, now)
    return {"child_execution_id": child_id, "task_id": claim["task_id"], "state": "canceled"}


def recover_child_execution(
    conn: sqlite3.Connection,
    claim_token: str,
    child_id: str,
    *,
    lease_seconds: int = 300,
) -> dict[str, object]:
    claim = _parent_claim(conn, claim_token, child_id)
    sweep_expired_child_executions(conn)
    child = _execution(conn, child_id)
    if child["state"] != "recovery_required":
        raise TodoError("child_not_recoverable", "Child execution is not awaiting recovery", ExitCode.BLOCKED)
    attempt, raw_token = _start_attempt(conn, child_id, lease_seconds)
    return {
        "child_execution_id": child_id,
        "task_id": claim["task_id"],
        "state": "running",
        "attempt": attempt,
        "child_token": raw_token,
    }


def child_execution_status(conn: sqlite3.Connection, claim_token: str, child_id: str) -> dict[str, object]:
    claim = _parent_claim(conn, claim_token, child_id)
    child = _execution(conn, child_id)
    scopes = [dict(row) for row in conn.execute(
        "SELECT path,state,acquired_at,released_at FROM child_scope_leases WHERE child_execution_id=? ORDER BY path",
        (child_id,),
    )]
    attempts = [dict(row) for row in conn.execute(
        "SELECT id,attempt_number,state,created_at,heartbeat_at,expires_at,completed_at,result_json "
        "FROM child_attempts WHERE child_execution_id=? ORDER BY attempt_number",
        (child_id,),
    )]
    for attempt in attempts:
        attempt["result"] = json.loads(attempt.pop("result_json") or "null")
    return {
        "child_execution_id": child_id,
        "task_id": claim["task_id"],
        "objective": child["objective"],
        "gates": json.loads(child["gates_json"]),
        "state": child["state"],
        "max_attempts": child["max_attempts"],
        "attempt_count": child["attempt_count"],
        "cancel_requested": bool(child["cancel_requested"]),
        "result": json.loads(child["result_json"] or "null"),
        "scopes": scopes,
        "attempts": attempts,
    }
