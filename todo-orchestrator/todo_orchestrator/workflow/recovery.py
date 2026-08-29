"""Owner-only workflow recovery planning and transactional execution.

Recovery is intentionally not capability-authorized: an interactive owner command
holds the project recovery lock and supplies a confirmed, freshly inspected plan.
This module never writes repository files or starts execution processes.
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import socket
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterator

from ..completion import recover_terminal_checkpoints, terminal_finalization_report
from ..config import utc_now
from ..git_state import scope_manifest
from ..models import ExitCode, TodoError
from ..ownership import release_claim_locks, scopes_for
from ..resources import local_process_alive
from .foundation import FINISH_TASK_BUDGET_BYTES, canonical_json, require_bounded_payload


ProcessProbe = Callable[[str | None, int | None, str | None], bool | None]
ChildProcessProbe = Callable[[dict[str, object]], bool | None]


ACTIVE_CHILD_STATES = frozenset({"authorized", "running", "recovery_required", "ready_for_acceptance", "succeeded"})
ACTIVE_DISPATCH_STATES = frozenset({"active"})
ACTIVE_CLAIM_STATES = frozenset({"active", "orphaned"})
ACTIVE_GATE_STATES = frozenset({"running"})


def _utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _expired(value: str | None, now: datetime) -> bool:
    parsed = _utc(value)
    return parsed is not None and parsed <= now


def default_process_probe(hostname: str | None, pid: int | None, process_start: str | None) -> bool | None:
    """Return True/False only for a locally observable process."""
    if hostname != socket.gethostname() or not pid:
        return None
    return local_process_alive(pid, process_start)


def unavailable_child_process_probe(child: dict[str, object]) -> bool | None:
    """Default until the local-worker supervisor adapter supplies status."""
    return None


def _sanitized_reason(value: str) -> str:
    return re.sub(r"\b(?:toc|tocs|toch|tor)_[A-Za-z0-9_-]+", "[redacted]", value)[:1000]


@contextmanager
def project_recovery_lock(database_path: Path) -> Iterator[Path]:
    """Hold one nonblocking project-level owner recovery lock."""
    lock_path = database_path.with_name(database_path.name + ".owner-recovery.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise TodoError(
                "recovery_lock_busy",
                "Another owner recovery operation holds the project recovery lock",
                ExitCode.CONTENTION,
            ) from exc
        yield lock_path
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


@dataclass(frozen=True)
class RecoveryEngine:
    """Fresh inspection and one coherent, revisioned recovery mutation."""

    database: object
    repo_root: Path
    project_uuid: str
    process_probe: ProcessProbe = default_process_probe
    child_process_probe: ChildProcessProbe = unavailable_child_process_probe
    actor_identity: str = "interactive-owner"

    def _process_state(self, row: dict[str, object]) -> str:
        observed = self.process_probe(
            row.get("hostname") if isinstance(row.get("hostname"), str) else None,
            int(row["pid"]) if row.get("pid") is not None else None,
            row.get("process_start") if isinstance(row.get("process_start"), str) else None,
        )
        if observed is True:
            return "live"
        if observed is False:
            return "stopped"
        return "unavailable"

    def _claim_dirty(self, conn, claim: dict[str, object]) -> tuple[bool, dict[str, object]]:
        roots = scopes_for(conn, str(claim["task_id"]), "exclusive")
        baseline = json.loads(str(claim.get("baseline_manifest_json") or "{}"))
        current = scope_manifest(self.repo_root, roots)
        return baseline.get("fingerprint") != current.get("fingerprint"), current

    def inspect(self, task_id: str | None = None) -> dict[str, object]:
        """Return a bounded proposed plan without changing authoritative state."""
        now = datetime.now(timezone.utc)
        actions: list[dict[str, object]] = []
        blockers: list[dict[str, object]] = []
        warnings: list[dict[str, object]] = []
        scope = " AND task_id=?" if task_id else ""
        args = (task_id,) if task_id else ()

        with self.database.read() as conn:
            meta_uuid = conn.execute("SELECT value FROM meta WHERE key='project_uuid'").fetchone()
            if not meta_uuid or str(meta_uuid[0]) != self.project_uuid:
                raise TodoError("recovery_project_mismatch", "Recovery project identity does not match the database")
            if task_id and not conn.execute("SELECT 1 FROM tasks WHERE id=?", (task_id,)).fetchone():
                raise TodoError("task_not_found", f"Unknown task {task_id}")

            dispatch_query = (
                "SELECT d.*,c.task_id FROM workflow_dispatches d JOIN claims c ON c.id=d.claim_id "
                "WHERE d.state='active'" + (" AND c.task_id=?" if task_id else "") + " ORDER BY d.id"
            )
            dispatches = [dict(row) for row in conn.execute(dispatch_query, args)]
            dispatch_claim_ids = {str(row["claim_id"]) for row in dispatches}
            recoverable_dispatch_claims: set[str] = set()
            blocked_dispatch_claims: set[str] = set()
            for dispatch in dispatches:
                state = self._process_state(dispatch)
                if state == "live" or (state == "unavailable" and not _expired(str(dispatch.get("heartbeat_at") or ""), now)):
                    blockers.append({"kind": "first_class_dispatch", "id": dispatch["id"], "state": state})
                    blocked_dispatch_claims.add(str(dispatch["claim_id"]))
                else:
                    recoverable_dispatch_claims.add(str(dispatch["claim_id"]))
                    actions.append({
                        "kind": "retire_dispatch", "id": dispatch["id"], "claim_id": dispatch["claim_id"],
                        "lane_id": dispatch["lane_id"], "task_id": dispatch["task_id"],
                    })

            claim_rows = [dict(row) for row in conn.execute(
                "SELECT c.*,s.hostname AS session_hostname,s.pid AS session_pid,s.process_start AS session_process_start "
                "FROM claims c JOIN sessions s ON s.id=c.session_id WHERE c.state IN ('active','orphaned')" + scope + " ORDER BY c.id",
                args,
            )]
            for claim in claim_rows:
                claim_id = str(claim["id"])
                if claim_id in blocked_dispatch_claims:
                    continue
                if claim_id not in recoverable_dispatch_claims:
                    process_row = {
                        "hostname": claim.get("session_hostname"), "pid": claim.get("session_pid"),
                        "process_start": claim.get("session_process_start"),
                    }
                    state = self._process_state(process_row)
                    expired = _expired(str(claim.get("expires_at") or ""), now)
                    if state == "live" or (state == "unavailable" and not expired and claim["state"] == "active"):
                        blockers.append({"kind": "claim_owner", "id": claim["id"], "task_id": claim["task_id"], "state": state})
                        continue
                dirty, manifest = self._claim_dirty(conn, claim)
                actions.append({
                    "kind": "release_claim", "id": claim["id"], "task_id": claim["task_id"],
                    "dirty": dirty, "current_fingerprint": manifest.get("fingerprint"),
                })
                if dirty:
                    warnings.append({"kind": "dirty_scope_preserved", "claim_id": claim["id"], "task_id": claim["task_id"]})

            child_query = (
                "SELECT c.*,a.id AS attempt_id,a.state AS attempt_state,a.expires_at AS attempt_expires_at "
                "FROM child_executions c LEFT JOIN child_attempts a ON a.child_execution_id=c.id AND a.state='active' "
                "WHERE c.state IN ('authorized','running','recovery_required','ready_for_acceptance','succeeded')"
                + (" AND c.task_id=?" if task_id else "") + " ORDER BY c.id"
            )
            for child in (dict(row) for row in conn.execute(child_query, args)):
                child_process = self.child_process_probe(child)
                if child_process is True:
                    blockers.append({
                        "kind": "local_child", "id": child["id"], "task_id": child["task_id"],
                        "state": "demonstrably_live",
                    })
                elif child_process is not False and child.get("attempt_id") and not _expired(str(child.get("attempt_expires_at") or ""), now):
                    blockers.append({
                        "kind": "local_child", "id": child["id"], "task_id": child["task_id"],
                        "state": "live_or_unproven",
                    })
                elif child["state"] in {"ready_for_acceptance", "succeeded"}:
                    blockers.append({
                        "kind": "local_child", "id": child["id"], "task_id": child["task_id"],
                        "state": "parent_acceptance_required",
                    })
                else:
                    candidates = conn.execute(
                        "SELECT id FROM workflow_child_result_candidates WHERE child_execution_id=? ORDER BY id", (child["id"],)
                    ).fetchall()
                    actions.append({
                        "kind": "terminalize_dead_child", "id": child["id"], "task_id": child["task_id"],
                        "attempt_id": child.get("attempt_id"), "preserved_candidate_ids": [row[0] for row in candidates],
                    })

            # A gate or leased process elsewhere in the project can still mutate
            # the same repository, so these safety blockers are always global.
            gate_query = "SELECT id,task_id,status FROM gates WHERE status='running' ORDER BY id"
            for gate in conn.execute(gate_query):
                blockers.append({"kind": "gate", "id": gate["id"], "task_id": gate["task_id"], "state": gate["status"]})

            lock_query = (
                "SELECT l.*,c.task_id FROM lock_leases l LEFT JOIN claims c ON c.id=l.claim_id "
                "WHERE l.state='active' ORDER BY l.id"
            )
            recovering_claim_ids = {str(item["id"]) for item in actions if item["kind"] == "release_claim"}
            for lease in (dict(row) for row in conn.execute(lock_query)):
                if str(lease.get("claim_id")) in recovering_claim_ids:
                    continue
                state = self._process_state(lease)
                expired = _expired(str(lease.get("expires_at") or ""), now)
                if state == "live" or (state == "unavailable" and not expired):
                    blockers.append({"kind": "lock", "id": lease["id"], "lock_name": lease["lock_name"], "state": state})
                else:
                    actions.append({"kind": "release_lock", "id": lease["id"], "state": state})

            lease_query = (
                "SELECT r.*,i.class_id FROM resource_leases r JOIN resource_instances i ON i.id=r.instance_id "
                "LEFT JOIN claims c ON c.id=r.claim_id WHERE r.state='active' ORDER BY r.id"
            )
            for lease in (dict(row) for row in conn.execute(lease_query)):
                state = self._process_state(lease)
                expired = _expired(str(lease.get("expires_at") or ""), now)
                if state == "live" or (state == "unavailable" and not expired):
                    blockers.append({
                        "kind": "resource", "id": lease["id"], "class_id": lease["class_id"], "state": state,
                    })
                else:
                    actions.append({"kind": "release_resource", "id": lease["id"], "state": state})

            workspace_query = (
                "SELECT DISTINCT w.* FROM workflow_workspaces w "
                "LEFT JOIN workflow_dispatches d ON d.workspace_id=w.id "
                "LEFT JOIN claims c ON c.id=d.claim_id "
                "WHERE w.state IN ('active','dirty','conflicted')"
                + (" AND (w.integration_task_id=? OR c.task_id=?)" if task_id else "") + " ORDER BY w.id"
            )
            workspace_args = (task_id, task_id) if task_id else ()
            for workspace in (dict(row) for row in conn.execute(workspace_query, workspace_args)):
                warnings.append({
                    "kind": "workspace_preserved", "id": workspace["id"], "state": workspace["state"],
                    "worktree_path": workspace.get("worktree_path"), "cleanup_eligible": False,
                })
                actions.append({"kind": "quarantine_workspace", "id": workspace["id"], "state": workspace["state"]})

            terminal_query = (
                "SELECT id FROM tasks WHERE status='done' AND result IN ('implemented','validated','evaluated_not_promoted','no_change_required')"
                + (" AND id=?" if task_id else "") + " ORDER BY id"
            )
            for task in conn.execute(terminal_query, args):
                if not conn.execute("SELECT 1 FROM checkpoints WHERE task_id=? AND state='pending'", (task["id"],)).fetchone():
                    continue
                try:
                    report = terminal_finalization_report(conn, str(task["id"]))
                except TodoError as error:
                    warnings.append({"kind": "terminal_checkpoint", "task_id": task["id"], "state": error.code})
                    continue
                if report["eligible"]:
                    actions.append({"kind": "finalize_terminal_checkpoints", "task_id": task["id"], "checkpoint_ids": report["eligible"]})

            pending_caps = [dict(row) for row in conn.execute(
                "SELECT id,claim_id,task_id FROM workflow_capabilities WHERE state='active'"
                + (" AND task_id=?" if task_id else "") + " ORDER BY id", args
            )]
            recovering_claims = {str(item["id"]) for item in actions if item["kind"] == "release_claim"}
            recovering_claims.update(str(item["claim_id"]) for item in actions if item["kind"] == "retire_dispatch")
            for capability in pending_caps:
                if str(capability.get("claim_id")) in recovering_claims:
                    actions.append({"kind": "retire_capability", "id": capability["id"], "task_id": capability["task_id"]})

            if not task_id:
                released_attention = conn.execute(
                    "SELECT DISTINCT t.id FROM tasks t "
                    "JOIN workflow_lane_tasks lt ON lt.task_id=t.id AND lt.state='queued' "
                    "JOIN workflow_lanes l ON l.id=lt.lane_id AND l.state='ready' "
                    "WHERE t.status='in_progress' AND t.attention_reason IS NOT NULL "
                    "AND NOT EXISTS(SELECT 1 FROM claims c WHERE c.task_id=t.id AND c.state='active') "
                    "AND EXISTS(SELECT 1 FROM claims c WHERE c.task_id=t.id AND c.state IN ('released','force_released','recovered_released')) "
                    "ORDER BY t.id"
                ).fetchall()
                actions.extend(
                    {"kind": "clear_released_attention", "task_id": str(row["id"])}
                    for row in released_attention
                )

        plan = {
            "project_uuid": self.project_uuid,
            "task_id": task_id,
            "status": "refused" if blockers else ("recovery_needed" if actions else "already_recovered"),
            "actions": actions,
            "blockers": blockers,
            "warnings": warnings,
            "file_policy": "preserve_all_no_repository_mutation",
        }
        require_bounded_payload(plan, limit=FINISH_TASK_BUDGET_BYTES, code="recovery_plan_too_large")
        return plan

    def execute(self, plan: dict[str, object], reason: str) -> dict[str, object]:
        """Execute a fresh, unblocked plan as one revisioned SQLite mutation."""
        reason = reason.strip()
        if not reason:
            raise TodoError("recovery_reason_required", "Owner recovery requires an explicit reason")
        fresh = self.inspect(plan.get("task_id") if isinstance(plan.get("task_id"), str) else None)
        if canonical_json(fresh) != canonical_json(plan):
            raise TodoError("recovery_plan_stale", "Recovery state changed after inspection", ExitCode.CONTENTION, fresh)
        if fresh["blockers"]:
            raise TodoError("recovery_live_work_refused", "Live or unproven mutable work prevents recovery", ExitCode.BLOCKED, fresh)
        if not fresh["actions"]:
            return {"status": "already_recovered", "project_uuid": self.project_uuid, "task_id": fresh["task_id"], "idempotent_noop": True}

        safe_reason = _sanitized_reason(reason)
        proposed = {key: fresh[key] for key in ("project_uuid", "task_id", "status", "actions", "warnings", "file_policy")}
        audit_id = str(uuid.uuid4())

        def operation(conn, revision):
            now = utc_now()
            results: list[dict[str, object]] = []
            dirty_tasks: set[str] = set()
            for action in fresh["actions"]:
                kind = str(action["kind"])
                if kind == "retire_dispatch":
                    conn.execute("UPDATE workflow_dispatches SET state='recovered',released_at=?,revision=? WHERE id=? AND state='active'", (now, revision, action["id"]))
                elif kind == "release_claim":
                    release_claim_locks(conn, str(action["id"]))
                    conn.execute("UPDATE resource_leases SET state='recovered',released_at=? WHERE claim_id=? AND state='active'", (now, action["id"]))
                    conn.execute("UPDATE claims SET state='recovered_released',released_at=? WHERE id=? AND state IN ('active','orphaned')", (now, action["id"]))
                    if action["dirty"]:
                        dirty_tasks.add(str(action["task_id"]))
                        conn.execute(
                            "INSERT INTO handoffs(id,task_id,claim_id,kind,note,payload_json,created_at,revision) VALUES(?,?,?,?,?,?,?,?)",
                            (str(uuid.uuid4()), action["task_id"], action["id"], "recovery_quarantine", "Owner recovery preserved dirty scope", json.dumps({"fingerprint": action["current_fingerprint"], "reason": safe_reason}, sort_keys=True), now, revision),
                        )
                        conn.execute("UPDATE tasks SET status='attention_required',attention_reason='recovery preserved dirty scope',updated_at=?,revision=? WHERE id=?", (now, revision, action["task_id"]))
                    else:
                        conn.execute("UPDATE tasks SET status='planned',attention_reason=NULL,updated_at=?,revision=? WHERE id=? AND status IN ('in_progress','attention_required')", (now, revision, action["task_id"]))
                    dispatch = conn.execute(
                        "SELECT lane_id FROM workflow_dispatches WHERE claim_id=? ORDER BY created_at DESC LIMIT 1",
                        (action["id"],),
                    ).fetchone()
                    if dispatch:
                        conn.execute(
                            "UPDATE workflow_lane_tasks SET state='queued',activated_at=NULL,revision=? "
                            "WHERE lane_id=? AND task_id=? AND state='active'",
                            (revision, dispatch["lane_id"], action["task_id"]),
                        )
                        conn.execute(
                            "UPDATE workflow_lanes SET state=?,updated_at=?,revision=? WHERE id=?",
                            ("attention_required" if action["dirty"] else "ready", now, revision, dispatch["lane_id"]),
                        )
                elif kind == "terminalize_dead_child":
                    if action.get("attempt_id"):
                        conn.execute("UPDATE child_attempts SET state='failed',completed_at=? WHERE id=? AND state='active'", (now, action["attempt_id"]))
                    conn.execute("UPDATE child_executions SET state='failed',completed_at=? WHERE id=? AND state IN ('authorized','running','recovery_required')", (now, action["id"]))
                    conn.execute("UPDATE child_scope_leases SET state='released',released_at=? WHERE child_execution_id=? AND state='active'", (now, action["id"]))
                elif kind == "release_resource":
                    conn.execute("UPDATE resource_leases SET state='recovered',released_at=? WHERE id=? AND state='active'", (now, action["id"]))
                elif kind == "release_lock":
                    conn.execute("UPDATE lock_leases SET state='recovered' WHERE id=? AND state='active'", (action["id"],))
                elif kind == "quarantine_workspace":
                    conn.execute("UPDATE workflow_workspaces SET state='quarantined',cleanup_eligible=0,updated_at=? WHERE id=?", (now, action["id"]))
                elif kind == "retire_capability":
                    conn.execute("UPDATE workflow_capabilities SET state='retired',revoked_at=? WHERE id=? AND state='active'", (now, action["id"]))
                elif kind == "clear_released_attention":
                    conn.execute(
                        "UPDATE tasks SET attention_reason=NULL,updated_at=?,revision=? "
                        "WHERE id=? AND status='in_progress'",
                        (now, revision, action["task_id"]),
                    )
                elif kind == "finalize_terminal_checkpoints":
                    results.append({"kind": kind, **recover_terminal_checkpoints(conn, self.repo_root, str(action["task_id"]), None, revision)})
                results.append({"kind": kind, "id": action.get("id"), "task_id": action.get("task_id")})
            result = {
                "status": "recovered", "project_uuid": self.project_uuid, "task_id": fresh["task_id"],
                "actions_applied": len(fresh["actions"]), "dirty_tasks": sorted(dirty_tasks),
                "resume": "next_task", "files_mutated": False, "details": results,
            }
            conn.execute(
                "INSERT INTO workflow_recovery_audit(id,project_uuid,task_id,reason,proposed_plan_json,result_json,actor_identity,created_at,completed_at,revision) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (audit_id, self.project_uuid, fresh["task_id"], safe_reason, canonical_json(proposed), canonical_json(result), self.actor_identity, now, now, revision),
            )
            return result

        result, revision = self.database.mutate(
            actor_session_id=None,
            entity_type="workflow_recovery",
            entity_id=str(fresh["task_id"] or self.project_uuid),
            event_type="workflow_recovery.completed",
            payload={"audit_id": audit_id, "task_id": fresh["task_id"], "reason": safe_reason},
            operation=operation,
        )
        response = {**result, "audit_id": audit_id, "project_revision": revision, "idempotent_noop": False}
        require_bounded_payload(response, limit=FINISH_TASK_BUDGET_BYTES, code="recovery_result_too_large")
        return response
