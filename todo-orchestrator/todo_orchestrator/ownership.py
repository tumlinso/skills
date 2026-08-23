"""Same-worktree ownership, named-lock, and guard semantics."""

from __future__ import annotations

import json
import os
import secrets
import socket
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import utc_now
from .git_state import canonical_relative, paths_overlap
from .models import ExitCode, TodoError
from .resources import local_process_alive, process_start
from .sessions import token_hash


def scopes_for(conn: sqlite3.Connection, task_id: str, mode: str | None = None) -> list[str]:
    if mode:
        rows = conn.execute("SELECT path FROM ownership_scopes WHERE task_id=? AND mode=? ORDER BY path", (task_id, mode))
    else:
        rows = conn.execute("SELECT path FROM ownership_scopes WHERE task_id=? ORDER BY path", (task_id,))
    return [row[0] for row in rows]


def _frozen_contract_read_allowed(conn: sqlite3.Connection, reader_task_id: str, writer_task_id: str, read_path: str, writer_root: str) -> bool:
    """A registered consumer may read a frozen contract while its owner continues.

    The owner still needs an explicit interface revision to change the contract;
    all non-contract paths retain ordinary exclusive/read conflict behavior.
    """
    for row in conn.execute(
        "SELECT i.contract_paths_json,i.state,i.version,ic.required_state,ic.required_version "
        "FROM interfaces i JOIN interface_consumers ic ON ic.interface_id=i.id "
        "WHERE i.owner_task_id=? AND ic.task_id=?",
        (writer_task_id, reader_task_id),
    ):
        if row["state"] != row["required_state"] or (row["required_version"] and row["version"] != row["required_version"]):
            continue
        for contract_path in __import__("json").loads(row["contract_paths_json"]):
            if paths_overlap(read_path, contract_path) and paths_overlap(writer_root, contract_path):
                return True
    return False


def sweep_lock_leases(conn: sqlite3.Connection) -> list[str]:
    now = utc_now()
    released: list[str] = []
    for lease in conn.execute("SELECT * FROM lock_leases WHERE state='active' AND expires_at<=?", (now,)):
        if lease["hostname"] == socket.gethostname() and local_process_alive(lease["pid"], lease["process_start"]):
            continue
        conn.execute("UPDATE lock_leases SET state='expired' WHERE id=?", (lease["id"],))
        released.append(lease["id"])
    return released


def ownership_conflicts(conn: sqlite3.Connection, task_id: str) -> list[dict[str, str]]:
    task = conn.execute("SELECT parallel_policy FROM tasks WHERE id=?", (task_id,)).fetchone()
    active = conn.execute(
        "SELECT c.task_id,t.parallel_policy FROM claims c JOIN tasks t ON t.id=c.task_id WHERE c.state='active' AND c.task_id<>?",
        (task_id,),
    ).fetchall()
    if not task:
        return [{"type": "missing_task", "task_id": task_id}]
    if task[0] in {"project_exclusive", "serial", "integration_exclusive"} and active:
        return [{"type": "parallel_policy", "task_id": row["task_id"]} for row in active]
    if any(row["parallel_policy"] in {"project_exclusive", "serial", "integration_exclusive"} for row in active):
        return [{"type": "active_parallel_policy", "task_id": row["task_id"]} for row in active]
    ours = scopes_for(conn, task_id, "exclusive")
    reads = scopes_for(conn, task_id, "read")
    if task[0] == "parallel_safe" and not ours and not conn.execute("SELECT 1 FROM task_locks WHERE task_id=?", (task_id,)).fetchone():
        return [{"type": "missing_scope", "task_id": task_id}]
    conflicts: list[dict[str, str]] = []
    for row in active:
        theirs = scopes_for(conn, row["task_id"], "exclusive")
        for our_path in ours:
            for their_path in theirs:
                if paths_overlap(our_path, their_path):
                    conflicts.append({"type": "path", "path": our_path, "other_path": their_path, "task_id": row["task_id"]})
        for read_path in reads:
            for their_path in theirs:
                if paths_overlap(read_path, their_path) and not _frozen_contract_read_allowed(conn, task_id, row["task_id"], read_path, their_path):
                    conflicts.append({"type": "path", "path": read_path, "other_path": their_path, "task_id": row["task_id"]})
    return conflicts


def acquire_task_locks(conn: sqlite3.Connection, task_id: str, claim_id: str, session_id: str, lease_seconds: int) -> list[dict[str, str]]:
    sweep_lock_leases(conn)
    names = [row[0] for row in conn.execute("SELECT lock_name FROM task_locks WHERE task_id=? AND phase='claim' ORDER BY lock_name", (task_id,))]
    acquired: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)
    for name in names:
        active = conn.execute("SELECT 1 FROM lock_leases WHERE lock_name=? AND state='active'", (name,)).fetchone()
        if active:
            raise TodoError("lock_unavailable", f"Named lock {name} is already leased", ExitCode.CONTENTION)
        raw = "tol_" + secrets.token_urlsafe(24)
        lease_id = str(uuid.uuid4())
        expires = (now + timedelta(seconds=lease_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO lock_leases(id,lock_name,claim_id,session_id,token_hash,state,acquired_at,heartbeat_at,expires_at,hostname,pid,process_start,command_json) VALUES(?,?,?,?,?,'active',?,?,?,?,?,?,?)",
            (lease_id, name, claim_id, session_id, token_hash(raw), utc_now(), utc_now(), expires, socket.gethostname(), os.getpid(), process_start(), "[]"),
        )
        acquired.append({"lease_id": lease_id, "name": name, "token": raw, "expires_at": expires})
    return acquired


def acquire_named_locks(
    conn: sqlite3.Connection,
    names: list[str],
    *,
    claim_id: str | None,
    session_id: str,
    lease_seconds: int,
    command: list[str] | None = None,
) -> list[dict[str, str]]:
    sweep_lock_leases(conn)
    acquired: list[dict[str, str]] = []
    now = datetime.now(timezone.utc)
    for name in sorted(set(names)):
        conn.execute("INSERT OR IGNORE INTO named_locks(name,capacity,metadata_json) VALUES(?,1,'{}')", (name,))
        if conn.execute("SELECT 1 FROM lock_leases WHERE lock_name=? AND state='active'", (name,)).fetchone():
            raise TodoError("lock_unavailable", f"Named lock {name} is already leased", ExitCode.CONTENTION)
        raw = "tol_" + secrets.token_urlsafe(24)
        lease_id = str(uuid.uuid4())
        expires = (now + timedelta(seconds=lease_seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        conn.execute(
            "INSERT INTO lock_leases(id,lock_name,claim_id,session_id,token_hash,state,acquired_at,heartbeat_at,expires_at,hostname,pid,process_start,command_json) VALUES(?,?,?,?,?,'active',?,?,?,?,?,?,?)",
            (lease_id, name, claim_id, session_id, token_hash(raw), utc_now(), utc_now(), expires, socket.gethostname(), os.getpid(), process_start(), json.dumps(command or [])),
        )
        acquired.append({"lease_id": lease_id, "name": name, "token": raw, "expires_at": expires})
    return acquired


def release_lock(conn: sqlite3.Connection, lease_token: str) -> dict[str, str]:
    row = conn.execute("SELECT * FROM lock_leases WHERE token_hash=? AND state='active'", (token_hash(lease_token),)).fetchone()
    if not row:
        raise TodoError("invalid_lock_token", "Named-lock token is invalid or inactive", ExitCode.INVALID_TOKEN)
    conn.execute("UPDATE lock_leases SET state='released',expires_at=? WHERE id=?", (utc_now(), row["id"]))
    return {"lease_id": row["id"], "name": row["lock_name"], "session_id": row["session_id"], "state": "released"}


def release_claim_locks(conn: sqlite3.Connection, claim_id: str) -> None:
    conn.execute("UPDATE lock_leases SET state='released',expires_at=? WHERE claim_id=? AND state='active'", (utc_now(), claim_id))


def guard_paths(conn: sqlite3.Connection, repo_root: Path, claim_id: str, paths: list[str]) -> dict[str, object]:
    claim = conn.execute("SELECT task_id FROM claims WHERE id=? AND state='active'", (claim_id,)).fetchone()
    if not claim:
        raise TodoError("claim_not_active", "The claim is not active", ExitCode.INVALID_TOKEN)
    normalized = [canonical_relative(repo_root, value) for value in paths]
    owned = scopes_for(conn, claim["task_id"], "exclusive")
    allowed = [path for path in normalized if any(path == root or path.startswith(root + "/") for root in owned)]
    denied = sorted(set(normalized) - set(allowed))
    if denied:
        raise TodoError("scope_violation", "Paths are outside the active claim's exclusive scope", ExitCode.BLOCKED, {"denied": denied})
    delegated: list[dict[str, str]] = []
    for lease in conn.execute(
        "SELECT l.child_execution_id,l.path FROM child_scope_leases l "
        "JOIN child_executions c ON c.id=l.child_execution_id "
        "WHERE c.parent_claim_id=? AND l.state='active'",
        (claim_id,),
    ):
        for path in allowed:
            if paths_overlap(path, lease["path"]):
                delegated.append({
                    "path": path,
                    "child_path": lease["path"],
                    "child_execution_id": lease["child_execution_id"],
                })
    if delegated:
        raise TodoError(
            "active_child_scope",
            "Cancel, supersede, reject, stale, or accept the delegated child before editing its paths",
            ExitCode.BLOCKED,
            {"conflicts": delegated},
        )
    return {"allowed": allowed, "task_id": claim["task_id"]}
