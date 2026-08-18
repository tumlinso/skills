"""Atomic claims, leases, orphan quarantine, release, and recovery."""

from __future__ import annotations

import json
import secrets
import socket
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import utc_now
from .git_state import git_head, scope_manifest
from .models import ExitCode, TodoError
from .ownership import acquire_task_locks, release_claim_locks, scopes_for
from .readiness import ready_tasks
from .resources import acquire_resource, local_process_alive
from .sessions import authenticate_claim, token_hash


def _iso_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sweep_expired(conn: sqlite3.Connection, repo_root: Path) -> list[dict[str, object]]:
    now = utc_now()
    swept: list[dict[str, object]] = []
    for claim in conn.execute("SELECT * FROM claims WHERE state='active' AND expires_at<=? ORDER BY expires_at", (now,)).fetchall():
        roots = scopes_for(conn, claim["task_id"], "exclusive")
        baseline = json.loads(claim["baseline_manifest_json"] or "{}")
        current = scope_manifest(repo_root, roots)
        clean = baseline.get("fingerprint") == current.get("fingerprint")
        release_claim_locks(conn, claim["id"])
        live_resources: list[str] = []
        for lease in conn.execute("SELECT * FROM resource_leases WHERE claim_id=? AND state='active'", (claim["id"],)):
            locally_alive = lease["hostname"] == socket.gethostname() and local_process_alive(lease["pid"], lease["process_start"])
            if locally_alive:
                live_resources.append(lease["id"])
            else:
                conn.execute("UPDATE resource_leases SET state='released',released_at=? WHERE id=?", (now, lease["id"]))
        if clean and not live_resources:
            conn.execute("UPDATE claims SET state='expired_clean',released_at=? WHERE id=?", (now, claim["id"]))
            conn.execute("UPDATE tasks SET status='planned',attention_reason=NULL,updated_at=? WHERE id=? AND status='in_progress'", (now, claim["task_id"]))
            state = "released_clean"
        else:
            reason = "owned paths changed after baseline" if not clean else "expired claim still has a demonstrably live local resource process"
            conn.execute("UPDATE claims SET state='orphaned',orphan_reason=? WHERE id=?", (reason, claim["id"]))
            conn.execute("UPDATE tasks SET status='attention_required',attention_reason=?,updated_at=? WHERE id=?", (reason, now, claim["task_id"]))
            state = "orphaned_dirty" if not clean else "orphaned_live_resource"
        swept.append({"claim_id": claim["id"], "task_id": claim["task_id"], "state": state, "current_manifest": current, "live_resource_leases": live_resources})
    return swept


def claim_best(
    conn: sqlite3.Connection,
    repo_root: Path,
    session_id: str,
    project_revision: int,
    lease_seconds: int,
    requested_task_id: str | None = None,
    *,
    reconcile_expired: bool = True,
) -> tuple[dict[str, object], str]:
    if reconcile_expired:
        sweep_expired(conn, repo_root)
    candidates = ready_tasks(conn)
    if requested_task_id:
        candidates = [item for item in candidates if item["task_id"] == requested_task_id]
    if not candidates:
        raise TodoError("no_actionable_work", "No safe task is currently claimable", ExitCode.NO_ACTIONABLE_WORK)
    candidate = candidates[0]
    task_id = str(candidate["task_id"])
    claim_id = str(uuid.uuid4())
    raw_token = "toc_" + secrets.token_urlsafe(36)
    roots = scopes_for(conn, task_id, "exclusive")
    baseline = scope_manifest(repo_root, roots)
    now = utc_now()
    expires = _iso_after(lease_seconds)
    try:
        conn.execute(
            "INSERT INTO claims(id,task_id,session_id,token_hash,state,created_at,heartbeat_at,expires_at,baseline_head,baseline_manifest_json,baseline_revision) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (claim_id, task_id, session_id, token_hash(raw_token), "active", now, now, expires, git_head(repo_root), json.dumps(baseline, sort_keys=True), project_revision),
        )
    except sqlite3.IntegrityError as exc:
        raise TodoError("claim_contention", f"Task {task_id} was claimed concurrently", ExitCode.CONTENTION) from exc
    conn.execute("UPDATE tasks SET status='in_progress',updated_at=?,version=version+1,revision=? WHERE id=?", (now, project_revision, task_id))
    locks = acquire_task_locks(conn, task_id, claim_id, session_id, lease_seconds)
    resources = []
    for request in conn.execute(
        "SELECT * FROM resource_requests WHERE task_id=? AND phase='claim' AND required=1 ORDER BY selector,id",
        (task_id,),
    ):
        for _ in range(int(request["amount"])):
            lease, lease_token = acquire_resource(
                conn,
                selector=request["selector"],
                session_id=session_id,
                claim_id=claim_id,
                request_id=request["id"],
                lease_seconds=lease_seconds,
            )
            lease["lease_token"] = lease_token
            resources.append(lease)
    return {
        "claim_id": claim_id,
        "task_id": task_id,
        "expires_at": expires,
        "baseline_head": git_head(repo_root),
        "baseline_manifest": baseline,
        "locks": locks,
        "resources": resources,
        "selection": candidate,
    }, raw_token


def pulse_claim(conn: sqlite3.Connection, claim_token: str, lease_seconds: int) -> dict[str, object]:
    claim = authenticate_claim(conn, claim_token)
    now = utc_now()
    expires = _iso_after(lease_seconds)
    conn.execute("UPDATE claims SET heartbeat_at=?,expires_at=? WHERE id=?", (now, expires, claim["id"]))
    conn.execute("UPDATE lock_leases SET heartbeat_at=?,expires_at=? WHERE claim_id=? AND state='active'", (now, expires, claim["id"]))
    conn.execute("UPDATE resource_leases SET heartbeat_at=?,expires_at=? WHERE claim_id=? AND state='active'", (now, expires, claim["id"]))
    return {"claim_id": claim["id"], "task_id": claim["task_id"], "session_id": claim["session_id"], "expires_at": expires}


def release_claim(conn: sqlite3.Connection, claim_token: str, *, next_status: str = "in_progress", reason: str | None = None) -> dict[str, object]:
    claim = authenticate_claim(conn, claim_token)
    now = utc_now()
    release_claim_locks(conn, claim["id"])
    conn.execute("UPDATE resource_leases SET state='released',released_at=? WHERE claim_id=? AND state='active'", (now, claim["id"]))
    conn.execute("UPDATE claims SET state='released',released_at=? WHERE id=?", (now, claim["id"]))
    conn.execute("UPDATE tasks SET status=?,attention_reason=?,updated_at=?,version=version+1 WHERE id=?", (next_status, reason, now, claim["task_id"]))
    return {"claim_id": claim["id"], "task_id": claim["task_id"], "session_id": claim["session_id"], "status": next_status}


def inspect_recovery(conn: sqlite3.Connection, repo_root: Path, task_id: str) -> dict[str, object]:
    claim = conn.execute("SELECT * FROM claims WHERE task_id=? AND state='orphaned' ORDER BY created_at DESC LIMIT 1", (task_id,)).fetchone()
    if not claim:
        raise TodoError("no_orphaned_claim", f"Task {task_id} has no orphaned claim")
    roots = scopes_for(conn, task_id, "exclusive")
    baseline = json.loads(claim["baseline_manifest_json"] or "{}")
    current = scope_manifest(repo_root, roots)
    return {"task_id": task_id, "claim_id": claim["id"], "baseline": baseline, "current": current, "clean": baseline.get("fingerprint") == current.get("fingerprint")}


def recover_release(conn: sqlite3.Connection, repo_root: Path, task_id: str, acknowledge_dirty: bool = False) -> dict[str, object]:
    report = inspect_recovery(conn, repo_root, task_id)
    if not report["clean"] and not acknowledge_dirty:
        raise TodoError("dirty_orphan_quarantined", "Owned paths changed; inspect or adopt before release", ExitCode.CONSISTENCY_ERROR, report)
    conn.execute("UPDATE claims SET state='recovered_released',released_at=? WHERE id=?", (utc_now(), report["claim_id"]))
    conn.execute("UPDATE tasks SET status='planned',attention_reason=NULL,updated_at=? WHERE id=?", (utc_now(), task_id))
    return report


def recover_adopt(conn: sqlite3.Connection, repo_root: Path, task_id: str, session_id: str, revision: int, lease_seconds: int) -> tuple[dict[str, object], str]:
    report = inspect_recovery(conn, repo_root, task_id)
    conn.execute("UPDATE claims SET state='adopted',released_at=? WHERE id=?", (utc_now(), report["claim_id"]))
    conn.execute("UPDATE tasks SET status='planned',attention_reason=NULL WHERE id=?", (task_id,))
    claim, token = claim_best(conn, repo_root, session_id, revision, lease_seconds, requested_task_id=task_id)
    claim["adopted_from"] = report["claim_id"]
    return claim, token
