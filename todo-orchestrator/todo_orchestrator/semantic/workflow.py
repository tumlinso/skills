"""Normalized additive read model for first-class workflow and subordinate children."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone


def _exists(conn, table: str) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _fresh(value: str | None, seconds: int) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed >= datetime.now(timezone.utc) - timedelta(seconds=seconds)


def workflow_state(conn, project: dict[str, object]) -> dict[str, object]:
    revision = int(conn.execute("SELECT value FROM meta WHERE key='project_revision'").fetchone()[0])
    if not _exists(conn, "workflow_runs"):
        return {
            "available": False,
            "reason": "workflow_semantic_read_unavailable",
            "revision": revision,
            "first_class_agents": [],
            "local_children": [],
        }
    freshness = int(project.get("configuration", {}).get("workflow_heartbeat_fresh_seconds", 180))
    runs: list[dict[str, object]] = []
    first_class: list[dict[str, object]] = []
    safe_parallel: list[list[str]] = []
    for run in conn.execute("SELECT * FROM workflow_runs ORDER BY created_at,id"):
        lanes: list[dict[str, object]] = []
        ready_lanes: list[str] = []
        for lane in conn.execute("SELECT * FROM workflow_lanes WHERE run_id=? ORDER BY parent_lane_id,id", (run["id"],)):
            queue = [
                {"position": int(row["position"]), "task_id": row["task_id"], "state": row["state"]}
                for row in conn.execute("SELECT position,task_id,state FROM workflow_lane_tasks WHERE lane_id=? ORDER BY position", (lane["id"],))
            ]
            dispatch = conn.execute(
                "SELECT d.*,s.state AS session_state,c.state AS claim_state,c.task_id AS claim_task "
                "FROM workflow_dispatches d JOIN sessions s ON s.id=d.session_id JOIN claims c ON c.id=d.claim_id "
                "WHERE d.lane_id=? AND d.state='active' ORDER BY d.created_at DESC LIMIT 1",
                (lane["id"],),
            ).fetchone()
            active_task = next((item for item in queue if item["state"] == "active"), None)
            workspace = conn.execute("SELECT * FROM workflow_workspaces WHERE run_id=? AND lane_id=?", (run["id"], lane["id"])).fetchone()
            observable = bool(
                dispatch
                and dispatch["session_state"] == "active"
                and dispatch["claim_state"] == "active"
                and active_task
                and dispatch["claim_task"] == active_task["task_id"]
                and int(dispatch["context_version"]) > 0
                and _fresh(dispatch["heartbeat_at"], freshness)
                and (lane["workspace_mode"] not in {"isolated_merge", "contract_split"} or workspace)
            )
            dispatch_view = None
            if dispatch:
                dispatch_view = {
                    "dispatch_id": dispatch["id"],
                    "session_id": dispatch["session_id"],
                    "claim_id": dispatch["claim_id"],
                    "task_id": dispatch["claim_task"],
                    "heartbeat_at": dispatch["heartbeat_at"],
                    "heartbeat_fresh": _fresh(dispatch["heartbeat_at"], freshness),
                    "hostname": dispatch["hostname"],
                    "pid": dispatch["pid"],
                    "process_start": dispatch["process_start"],
                    "context_version": int(dispatch["context_version"]),
                    "observable": observable,
                }
                if observable:
                    first_class.append({
                        "run_id": run["id"], "lane_id": lane["id"], "role": lane["role"], **dispatch_view,
                    })
            if lane["state"] == "ready" and queue and queue[0]["state"] == "queued" and not dispatch:
                ready_lanes.append(str(lane["id"]))
            lanes.append({
                "id": lane["id"], "parent_lane_id": lane["parent_lane_id"], "role": lane["role"],
                "state": lane["state"], "workspace_mode": lane["workspace_mode"],
                "context_cursor": int(lane["context_cursor"]), "queue": queue,
                "dispatch": dispatch_view, "workspace": dict(workspace) if workspace else None,
            })
        if len(ready_lanes) > 1:
            safe_parallel.append(sorted(ready_lanes))
        runs.append({
            "id": run["id"], "root_task_id": run["root_task_id"], "status": run["status"],
            "active_charter_version": int(run["active_charter_version"]), "lanes": lanes,
        })
    messages = [
        {
            "id": row["id"], "run_id": row["run_id"], "author_lane_id": row["author_lane_id"],
            "task_id": row["task_id"], "kind": row["kind"], "blocking": bool(row["blocking"]),
            "state": row["state"], "revision": int(row["revision"]),
        }
        for row in conn.execute("SELECT * FROM workflow_messages WHERE state='open' AND (blocking=1 OR kind='question') ORDER BY revision,id")
    ]
    rendezvous = []
    for row in conn.execute("SELECT * FROM workflow_rendezvous ORDER BY run_id,id"):
        arrivals = [dict(item) for item in conn.execute(
            "SELECT lane_id,task_id,state,context_version,revision FROM workflow_rendezvous_arrivals WHERE rendezvous_id=? ORDER BY lane_id",
            (row["id"],),
        )]
        rendezvous.append({
            "id": row["id"], "run_id": row["run_id"], "barrier_id": row["barrier_id"],
            "mode": row["mode"], "quorum": row["quorum"], "join_task_id": row["join_task_id"],
            "state": row["state"], "arrivals": arrivals,
        })
    integrations = [
        {
            "id": row["id"], "run_id": row["run_id"], "integration_task_id": row["integration_task_id"],
            "integrator_lane_id": row["integrator_lane_id"], "position": int(row["position"]),
            "state": row["state"], "conflict": json.loads(row["conflict_json"] or "{}"),
        }
        for row in conn.execute("SELECT * FROM workflow_integration_queue ORDER BY run_id,integration_task_id,position")
    ]
    local_children = [
        {
            "child_execution_id": row["id"], "parent_claim_id": row["parent_claim_id"],
            "parent_task_id": row["task_id"], "parent_lane_id": row["parent_lane_id"],
            "state": row["state"], "access_mode": row["access_mode"],
        }
        for row in conn.execute(
            "SELECT c.*,d.lane_id AS parent_lane_id FROM child_executions c "
            "LEFT JOIN workflow_dispatches d ON d.claim_id=c.parent_claim_id AND d.state='active' ORDER BY c.created_at,c.id"
        )
    ]
    recovery_needed = [
        {"kind": "dispatch", "id": row["id"], "reason": "stale_heartbeat"}
        for row in conn.execute("SELECT id,heartbeat_at FROM workflow_dispatches WHERE state='active'")
        if not _fresh(row["heartbeat_at"], freshness)
    ]
    recovery_needed.extend(
        {"kind": "workspace", "id": row["id"], "reason": row["state"]}
        for row in conn.execute(
            "SELECT id,state FROM workflow_workspaces WHERE state IN ('conflict','apply_failed','finalization_failed','quarantined','provisioning_failed')"
        )
    )
    return {
        "available": True,
        "revision": revision,
        "active_run_id": next((str(run["id"]) for run in runs if run["status"] == "active"), None),
        "runs": runs,
        "first_class_agents": first_class,
        "local_children": local_children,
        "blocking_messages": messages,
        "unresolved_questions": [item for item in messages if item["kind"] == "question"],
        "rendezvous": rendezvous,
        "integration_queue": integrations,
        "recovery_needed": recovery_needed,
        "safe_parallel_groups": safe_parallel,
    }
