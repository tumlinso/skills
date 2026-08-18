"""Compact project status, blocker-frontier, and handoff reporting."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from .readiness import explain_task, ready_tasks


def project_status(conn: sqlite3.Connection) -> dict[str, object]:
    revision = int(conn.execute("SELECT value FROM meta WHERE key='project_revision'").fetchone()[0])
    counts = {row["status"]: row["count"] for row in conn.execute("SELECT status,COUNT(*) AS count FROM tasks GROUP BY status")}
    active = [dict(row) for row in conn.execute(
        "SELECT c.id AS claim_id,c.task_id,c.expires_at,s.label FROM claims c JOIN sessions s ON s.id=c.session_id WHERE c.state='active' ORDER BY c.task_id"
    )]
    orphaned = [dict(row) for row in conn.execute("SELECT id AS claim_id,task_id,orphan_reason FROM claims WHERE state='orphaned' ORDER BY task_id")]
    barriers = [dict(row) for row in conn.execute("SELECT id,state,explanation FROM barriers ORDER BY id")]
    return {"project_revision": revision, "task_counts": counts, "ready": ready_tasks(conn), "active_claims": active, "orphaned_claims": orphaned, "barriers": barriers}


def no_work_frontier(conn: sqlite3.Connection) -> dict[str, object]:
    explanations = []
    for row in conn.execute("SELECT id FROM tasks WHERE status NOT IN ('done','superseded','cancelled','stale') AND kind<>'epic' ORDER BY priority DESC,id LIMIT 100"):
        report = explain_task(conn, row["id"])
        if not report["ready"]:
            explanations.append(report)
    active = [dict(row) for row in conn.execute("SELECT c.task_id,s.label,c.expires_at FROM claims c JOIN sessions s ON s.id=c.session_id WHERE c.state='active' ORDER BY c.task_id")]
    unavailable = [dict(row) for row in conn.execute(
        "SELECT ri.id,ri.class_id,ri.capacity,COUNT(rl.id) AS active FROM resource_instances ri LEFT JOIN resource_leases rl ON rl.instance_id=ri.id AND rl.state='active' GROUP BY ri.id HAVING active>=ri.capacity"
    )]
    barriers = [dict(row) for row in conn.execute("SELECT id,explanation FROM barriers WHERE state<>'open' ORDER BY id")]
    orphaned = [dict(row) for row in conn.execute("SELECT task_id,orphan_reason FROM claims WHERE state='orphaned' ORDER BY task_id")]
    return {"active_work": active, "blocker_frontier": explanations, "unopened_barriers": barriers, "orphaned_claims": orphaned, "unavailable_resources": unavailable, "most_likely_next_transition": explanations[0] if explanations else None}


def git_diffstat(repo_root: Path) -> str:
    result = subprocess.run(["git", "-C", str(repo_root), "diff", "--stat"], capture_output=True, text=True, check=False)
    return result.stdout.strip()
