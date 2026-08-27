"""Managed first-class lane workspaces and integration queues.

Git worktrees provide mutation isolation; todo SQLite remains the semantic
authority.  This module deliberately has no cleanup operation: dirty or
conflicted work is preserved, and cleanup only becomes *eligible* after an
explicit, validated state transition.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable, Sequence

from ..config import utc_now
from ..models import TodoError
from .foundation import WORKSPACE_MODES, WorkflowDatabase


Runner = Callable[..., subprocess.CompletedProcess[bytes]]
_BRANCH = re.compile(r"^(?![-.])(?!.*(?:\.\.|@\{|//|[\\ ~^:?*\[]))(?!.*[/.]$).+$")


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class WorkspaceService:
    """Transactional workspace state plus conservative Git operations."""

    def __init__(self, db: WorkflowDatabase, *, managed_root: Path, runner: Runner | None = None):
        self.db = db
        self.managed_root = managed_root.resolve()
        self.runner = runner or subprocess.run

    def _git(self, repo: Path, args: Sequence[str], *, text: bool = False) -> subprocess.CompletedProcess[Any]:
        return self.runner(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            check=False,
            text=text,
        )

    def _git_ok(self, repo: Path, args: Sequence[str], *, code: str) -> bytes:
        result = self._git(repo, args)
        if result.returncode != 0:
            raise TodoError(code, "Git operation failed", details={"returncode": result.returncode})
        return result.stdout

    def _managed_path(self, value: Path) -> Path:
        target = value.resolve()
        try:
            target.relative_to(self.managed_root)
        except ValueError as exc:
            raise TodoError("workspace_path_unmanaged", "Workspace path must be below the managed state root") from exc
        if target == self.managed_root:
            raise TodoError("workspace_path_unmanaged", "Managed state root cannot itself be a workspace")
        return target

    def _commit(self, repository_root: Path, ref: str) -> str:
        raw = self._git_ok(repository_root, ["rev-parse", "--verify", f"{ref}^{{commit}}"], code="workspace_base_missing")
        return raw.decode("utf-8", errors="replace").strip()

    def _lane(self, conn: Any, run_id: str, lane_id: str) -> Any:
        row = conn.execute(
            "SELECT id,run_id,role,workspace_mode,state FROM workflow_lanes WHERE id=? AND run_id=?",
            (lane_id, run_id),
        ).fetchone()
        if row is None:
            raise TodoError("workspace_lane_missing", "Workspace requires a first-class lane in the active run")
        return row

    def create_workspace(
        self,
        *,
        repository_root: Path,
        repository_identity: str,
        run_id: str,
        lane_id: str,
        mode: str,
        base_commit: str,
        worktree_path: Path | None,
        branch: str | None,
        integration_task_id: str | None,
        actor_session_id: str | None = None,
        worker_class: str = "first_class",
    ) -> dict[str, object]:
        """Materialize and record a managed first-class workspace.

        If the semantic record cannot be written after Git creates the worktree,
        the worktree is intentionally left in place for owner inspection.
        """
        if worker_class != "first_class":
            raise TodoError("local_child_workspace_forbidden", "Local-worker children cannot own first-class lane workspaces")
        if mode not in WORKSPACE_MODES:
            raise TodoError("invalid_workspace_mode", f"Unsupported workspace mode: {mode}")
        repository_root = repository_root.resolve()
        if not repository_identity:
            raise TodoError("repository_identity_required", "Repository identity is required")
        canonical_base = self._commit(repository_root, base_commit)
        target: Path | None = None
        if mode != "read_shared":
            if worktree_path is None:
                raise TodoError("workspace_path_required", f"{mode} requires a managed worktree path")
            target = self._managed_path(worktree_path)
            if target.exists():
                raise TodoError("workspace_path_exists", "Managed worktree path already exists")
            if branch is not None and not _BRANCH.match(branch):
                raise TodoError("invalid_workspace_branch", "Workspace branch name is unsafe or invalid")
        elif worktree_path is not None or branch is not None:
            raise TodoError("read_shared_materialization_forbidden", "read_shared does not create a writable worktree")
        if mode == "isolated_merge" and not integration_task_id:
            raise TodoError("integration_task_required", "isolated_merge requires an explicit integration task")

        workspace_id = str(uuid.uuid4())
        now = utc_now()

        def record(conn: Any, revision: int) -> dict[str, object]:
            lane = self._lane(conn, run_id, lane_id)
            if lane["workspace_mode"] != mode:
                raise TodoError("lane_workspace_mode_mismatch", "Workspace mode differs from the lane contract")
            if mode == "isolated_merge":
                stale = conn.execute(
                    """SELECT id,base_commit FROM workflow_workspaces
                       WHERE run_id=? AND integration_task_id=? AND mode='isolated_merge' AND base_commit<>?""",
                    (run_id, integration_task_id, canonical_base),
                ).fetchone()
                if stale is not None:
                    raise TodoError(
                        "workspace_base_mismatch",
                        "All isolated participants for an integration task must start from the exact same base commit",
                        details={"existing_workspace_id": stale["id"]},
                    )
            conn.execute(
                """INSERT INTO workflow_workspaces(
                     id,repository_identity,run_id,lane_id,mode,base_commit,worktree_path,branch,state,
                     integration_task_id,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    workspace_id, repository_identity, run_id, lane_id, mode, canonical_base,
                    str(target) if target else None, branch, "active", integration_task_id, now, now,
                ),
            )
            return {"workspace_id": workspace_id, "run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base}

        # Validate all semantic conditions before touching Git. A second check in
        # the mutation below closes races between parallel lane registrations.
        with self.db.read() as conn:
            lane = self._lane(conn, run_id, lane_id)
            if lane["workspace_mode"] != mode:
                raise TodoError("lane_workspace_mode_mismatch", "Workspace mode differs from the lane contract")
            if conn.execute("SELECT 1 FROM workflow_workspaces WHERE run_id=? AND lane_id=?", (run_id, lane_id)).fetchone():
                raise TodoError("workspace_already_exists", "Lane already has a managed workspace")
            if mode == "isolated_merge" and conn.execute(
                """SELECT 1 FROM workflow_workspaces WHERE run_id=? AND integration_task_id=?
                   AND mode='isolated_merge' AND base_commit<>?""",
                (run_id, integration_task_id, canonical_base),
            ).fetchone():
                raise TodoError("workspace_base_mismatch", "All isolated participants must use the exact same base")

        if target is not None:
            target.parent.mkdir(parents=True, exist_ok=True)
            args = ["worktree", "add"]
            if branch:
                args.extend(["-b", branch])
            else:
                args.append("--detach")
            args.extend([str(target), canonical_base])
            self._git_ok(repository_root, args, code="workspace_materialization_failed")

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_workspace",
            entity_id=workspace_id,
            event_type="workflow_workspace_created",
            payload={"run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base},
            operation=record,
        )
        result["revision"] = revision
        result["worktree_path"] = str(target) if target else None
        return result

    def publish_artifact(
        self,
        *,
        workspace_id: str,
        task_id: str,
        kind: str,
        artifact_ref: str,
        actor_session_id: str | None = None,
    ) -> dict[str, object]:
        if kind not in {"commit", "patch"}:
            raise TodoError("invalid_patch_artifact_kind", "Artifact kind must be commit or patch")
        with self.db.read() as conn:
            workspace = conn.execute("SELECT * FROM workflow_workspaces WHERE id=?", (workspace_id,)).fetchone()
            if workspace is None:
                raise TodoError("workspace_missing", "Workspace does not exist")
            if workspace["mode"] != "isolated_merge":
                raise TodoError("workspace_artifact_forbidden", "Only isolated_merge lanes publish integration artifacts")
            root = Path(workspace["worktree_path"])
            base = workspace["base_commit"]
        if kind == "commit":
            resolved = self._commit(root, artifact_ref)
            ancestry = self._git(root, ["merge-base", "--is-ancestor", base, resolved])
            if ancestry.returncode != 0:
                raise TodoError("artifact_base_mismatch", "Commit artifact is not based on the recorded workspace base")
            artifact_ref = resolved
            content = self._git_ok(root, ["diff", "--binary", base, resolved], code="artifact_diff_failed")
        else:
            patch = Path(artifact_ref).resolve()
            if not patch.is_file():
                raise TodoError("patch_artifact_missing", "Patch artifact file does not exist")
            content = patch.read_bytes()
            if not content:
                raise TodoError("patch_artifact_empty", "Patch artifact must not be empty")
            artifact_ref = str(patch)
        digest = _sha256(content)
        artifact_id = str(uuid.uuid4())
        now = utc_now()

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state,base_commit FROM workflow_workspaces WHERE id=?", (workspace_id,)).fetchone()
            if current is None or current["state"] not in {"active", "artifact_ready"}:
                raise TodoError("workspace_artifact_state", "Workspace is not eligible to publish an artifact")
            conn.execute(
                """INSERT INTO workflow_patch_artifacts(
                     id,workspace_id,task_id,kind,artifact_ref,content_hash,base_commit,created_at,state)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (artifact_id, workspace_id, task_id, kind, artifact_ref, digest, current["base_commit"], now, "pending"),
            )
            conn.execute(
                """UPDATE workflow_workspaces SET state='artifact_ready',artifact_kind=?,artifact_ref=?,
                   diff_hash=?,updated_at=? WHERE id=?""",
                (kind, artifact_ref, digest, now, workspace_id),
            )
            return {"artifact_id": artifact_id, "workspace_id": workspace_id, "kind": kind, "artifact_ref": artifact_ref, "diff_hash": digest}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_patch_artifact",
            entity_id=artifact_id,
            event_type="workflow_patch_artifact_published",
            payload={"workspace_id": workspace_id, "task_id": task_id, "kind": kind, "content_hash": digest},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def enqueue_artifact(
        self,
        *,
        artifact_id: str,
        integrator_lane_id: str,
        integration_task_id: str,
        actor_session_id: str | None = None,
    ) -> dict[str, object]:
        queue_id = str(uuid.uuid4())
        now = utc_now()

        def operation(conn: Any, revision: int) -> dict[str, object]:
            artifact = conn.execute(
                """SELECT a.*,w.run_id,w.integration_task_id AS declared_task,w.repository_identity
                   FROM workflow_patch_artifacts a JOIN workflow_workspaces w ON w.id=a.workspace_id
                   WHERE a.id=?""",
                (artifact_id,),
            ).fetchone()
            if artifact is None or artifact["state"] != "pending":
                raise TodoError("artifact_not_queueable", "Artifact is missing or is not pending")
            if artifact["declared_task"] != integration_task_id:
                raise TodoError("integration_task_mismatch", "Artifact was not declared for this integration task")
            lane = self._lane(conn, artifact["run_id"], integrator_lane_id)
            if lane["role"] != "integrator":
                raise TodoError("integrator_role_required", "Integration queue ownership requires an integrator lane")
            destination = conn.execute(
                """SELECT * FROM workflow_workspaces WHERE run_id=? AND lane_id=?""",
                (artifact["run_id"], integrator_lane_id),
            ).fetchone()
            if destination is None or destination["mode"] != "exclusive":
                raise TodoError("exclusive_integration_workspace_required", "Integrator must exclusively own the destination workspace")
            if destination["repository_identity"] != artifact["repository_identity"]:
                raise TodoError("integration_repository_mismatch", "Producer and destination repositories differ")
            if destination["base_commit"] != artifact["base_commit"]:
                raise TodoError("integration_stale_base", "Producer and destination must have the exact same recorded base")
            position = conn.execute(
                "SELECT COALESCE(MAX(position),-1)+1 FROM workflow_integration_queue WHERE run_id=? AND integration_task_id=?",
                (artifact["run_id"], integration_task_id),
            ).fetchone()[0]
            conn.execute(
                """INSERT INTO workflow_integration_queue(
                     id,run_id,integration_task_id,integrator_lane_id,patch_artifact_id,position,state,
                     conflict_json,merge_result_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,'{}','{}',?,?)""",
                (queue_id, artifact["run_id"], integration_task_id, integrator_lane_id, artifact_id, position, "queued", now, now),
            )
            conn.execute("UPDATE workflow_patch_artifacts SET state='queued' WHERE id=?", (artifact_id,))
            conn.execute("UPDATE workflow_workspaces SET state='queued',updated_at=? WHERE id=?", (now, artifact["workspace_id"]))
            return {"queue_id": queue_id, "position": position, "run_id": artifact["run_id"], "artifact_id": artifact_id}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_artifact_queued",
            payload={"artifact_id": artifact_id, "integrator_lane_id": integrator_lane_id, "integration_task_id": integration_task_id},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def apply_next(self, *, queue_id: str, actor_session_id: str | None = None) -> dict[str, object]:
        with self.db.read() as conn:
            row = conn.execute(
                """SELECT q.*,a.kind,a.artifact_ref,a.content_hash,a.base_commit,a.workspace_id,
                          d.worktree_path AS destination_path,d.state AS destination_state
                   FROM workflow_integration_queue q
                   JOIN workflow_patch_artifacts a ON a.id=q.patch_artifact_id
                   JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id
                   WHERE q.id=?""",
                (queue_id,),
            ).fetchone()
            if row is None or row["state"] != "queued":
                raise TodoError("integration_not_queueable", "Queue entry is missing or is not queued")
            earlier = conn.execute(
                """SELECT id FROM workflow_integration_queue WHERE run_id=? AND integration_task_id=?
                   AND position<? AND state NOT IN ('integrated','rejected') ORDER BY position LIMIT 1""",
                (row["run_id"], row["integration_task_id"], row["position"]),
            ).fetchone()
            if earlier is not None:
                raise TodoError("integration_queue_order", "An earlier integration entry must finish first")
            destination = Path(row["destination_path"])
        if not destination.exists():
            raise TodoError("integration_workspace_missing", "Destination integration workspace is unavailable")
        status = self._git_ok(destination, ["status", "--porcelain=v1", "-z"], code="integration_status_failed")
        if status:
            raise TodoError("integration_workspace_dirty", "Destination has dirty changes; all files are preserved")
        if row["kind"] == "commit":
            current = self._commit(destination, row["artifact_ref"])
            diff = self._git_ok(destination, ["diff", "--binary", row["base_commit"], current], code="artifact_diff_failed")
            if _sha256(diff) != row["content_hash"]:
                raise TodoError("artifact_content_changed", "Commit artifact no longer matches its immutable hash")
            command = ["cherry-pick", "--no-commit", current]
        else:
            patch = Path(row["artifact_ref"])
            content = patch.read_bytes() if patch.is_file() else b""
            if _sha256(content) != row["content_hash"]:
                raise TodoError("artifact_content_changed", "Patch artifact no longer matches its immutable hash")
            command = ["apply", "--index", "--3way", str(patch)]
        applied = self._git(destination, command)
        conflicts: list[str] = []
        if applied.returncode != 0:
            unresolved = self._git(destination, ["diff", "--name-only", "--diff-filter=U"])
            conflicts = sorted(filter(None, unresolved.stdout.decode("utf-8", errors="replace").splitlines()))
        now = utc_now()
        state = "awaiting_gates" if applied.returncode == 0 else "conflict"
        merge_result = {"returncode": applied.returncode, "state": state}
        conflict = {
            "paths": conflicts,
            "integration_task_id": row["integration_task_id"],
            "preserved": applied.returncode != 0,
        } if applied.returncode != 0 else {}

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state FROM workflow_integration_queue WHERE id=?", (queue_id,)).fetchone()
            if current is None or current["state"] != "queued":
                raise TodoError("integration_state_changed", "Integration queue entry changed while Git was applying")
            conn.execute(
                "UPDATE workflow_integration_queue SET state=?,conflict_json=?,merge_result_json=?,updated_at=? WHERE id=?",
                (state, _json(conflict), _json(merge_result), now, queue_id),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state=?,merge_result_json=?,updated_at=? WHERE run_id=? AND lane_id=?",
                (state, _json(merge_result), now, row["run_id"], row["integrator_lane_id"]),
            )
            return {"queue_id": queue_id, "state": state, "conflict": conflict, "integration_task_id": row["integration_task_id"]}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_integration_applied" if applied.returncode == 0 else "workflow_integration_conflict",
            payload={"state": state, "conflict_paths": conflicts},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def record_post_merge_gates(
        self,
        *,
        queue_id: str,
        gate_results: Sequence[dict[str, object]],
        actor_session_id: str | None = None,
    ) -> dict[str, object]:
        if not gate_results:
            raise TodoError("post_merge_gates_required", "At least one post-merge gate result is required")
        passed = all(item.get("status") == "passed" for item in gate_results)
        now = utc_now()
        target_state = "integrated" if passed else "gate_failed"

        def operation(conn: Any, revision: int) -> dict[str, object]:
            row = conn.execute(
                """SELECT q.*,a.workspace_id FROM workflow_integration_queue q
                   JOIN workflow_patch_artifacts a ON a.id=q.patch_artifact_id WHERE q.id=?""",
                (queue_id,),
            ).fetchone()
            if row is None or row["state"] != "awaiting_gates":
                raise TodoError("integration_not_awaiting_gates", "Integration is not awaiting post-merge gates")
            merge_result = {"state": target_state, "gates": list(gate_results)}
            conn.execute(
                "UPDATE workflow_integration_queue SET state=?,merge_result_json=?,updated_at=? WHERE id=?",
                (target_state, _json(merge_result), now, queue_id),
            )
            conn.execute("UPDATE workflow_patch_artifacts SET state=? WHERE id=?", (target_state, row["patch_artifact_id"]))
            conn.execute(
                "UPDATE workflow_workspaces SET state=?,merge_result_json=?,updated_at=? WHERE id=?",
                (target_state, _json(merge_result), now, row["workspace_id"]),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state=?,merge_result_json=?,updated_at=? WHERE run_id=? AND lane_id=?",
                (target_state, _json(merge_result), now, row["run_id"], row["integrator_lane_id"]),
            )
            return {"queue_id": queue_id, "state": target_state, "gates": list(gate_results)}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_post_merge_gates_recorded",
            payload={"state": target_state, "gate_count": len(gate_results)},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def reject_artifact(self, *, artifact_id: str, actor_session_id: str | None = None) -> dict[str, object]:
        now = utc_now()

        def operation(conn: Any, revision: int) -> dict[str, object]:
            row = conn.execute("SELECT workspace_id,state FROM workflow_patch_artifacts WHERE id=?", (artifact_id,)).fetchone()
            if row is None or row["state"] not in {"pending", "queued"}:
                raise TodoError("artifact_not_rejectable", "Artifact is missing or already terminal")
            conn.execute("UPDATE workflow_patch_artifacts SET state='rejected' WHERE id=?", (artifact_id,))
            conn.execute("UPDATE workflow_workspaces SET state='rejected',updated_at=? WHERE id=?", (now, row["workspace_id"]))
            conn.execute(
                "UPDATE workflow_integration_queue SET state='rejected',updated_at=? WHERE patch_artifact_id=? AND state='queued'",
                (now, artifact_id),
            )
            return {"artifact_id": artifact_id, "workspace_id": row["workspace_id"], "state": "rejected"}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_patch_artifact",
            entity_id=artifact_id,
            event_type="workflow_patch_artifact_rejected",
            payload={"state": "rejected"},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def mark_cleanup_eligible(self, *, workspace_id: str, actor_session_id: str | None = None) -> dict[str, object]:
        with self.db.read() as conn:
            row = conn.execute("SELECT state,worktree_path FROM workflow_workspaces WHERE id=?", (workspace_id,)).fetchone()
            if row is None:
                raise TodoError("workspace_missing", "Workspace does not exist")
            if row["state"] not in {"integrated", "rejected"}:
                raise TodoError("workspace_cleanup_not_terminal", "Only integrated or explicitly rejected work can become cleanup eligible")
            path = Path(row["worktree_path"]) if row["worktree_path"] else None
        if path is not None:
            if not path.exists():
                raise TodoError("workspace_missing", "Workspace path is unavailable; no cleanup state was changed")
            if self._git_ok(path, ["status", "--porcelain=v1", "-z"], code="workspace_status_failed"):
                raise TodoError("workspace_dirty_preserved", "Dirty or conflicted workspace is preserved and cannot become cleanup eligible")
        now = utc_now()

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state,cleanup_eligible FROM workflow_workspaces WHERE id=?", (workspace_id,)).fetchone()
            if current is None or current["state"] not in {"integrated", "rejected"}:
                raise TodoError("workspace_cleanup_state_changed", "Workspace state changed during cleanup assessment")
            conn.execute("UPDATE workflow_workspaces SET cleanup_eligible=1,updated_at=? WHERE id=?", (now, workspace_id))
            return {"workspace_id": workspace_id, "cleanup_eligible": True, "deleted": False}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_workspace",
            entity_id=workspace_id,
            event_type="workflow_workspace_cleanup_eligible",
            payload={"cleanup_eligible": True, "deleted": False},
            operation=operation,
        )
        result["revision"] = revision
        return result
