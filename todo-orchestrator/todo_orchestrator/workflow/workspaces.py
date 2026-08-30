"""Managed first-class lane workspaces and integration queues.

Git worktrees provide mutation isolation; todo SQLite remains the semantic
authority.  This module deliberately has no cleanup operation: dirty or
conflicted work is preserved, and cleanup only becomes *eligible* after an
explicit, validated state transition.
"""

from __future__ import annotations

import hashlib
import json
import os
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


def _write_immutable(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise TodoError("artifact_hash_collision", "Managed artifact hash collision")
        return
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, 0o444)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


class WorkspaceService:
    """Transactional workspace state plus conservative Git operations."""

    def __init__(
        self,
        db: WorkflowDatabase,
        *,
        managed_root: Path,
        runner: Runner | None = None,
        repository_identity_resolver: Callable[[Path], str] | None = None,
    ):
        self.db = db
        self.managed_root = managed_root.resolve()
        self.runner = runner or subprocess.run
        self.repository_identity_resolver = repository_identity_resolver

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

    def _git_input_ok(self, repo: Path, args: Sequence[str], content: bytes, *, code: str) -> bytes:
        result = self.runner(
            ["git", "-C", str(repo), *args],
            input=content,
            capture_output=True,
            check=False,
        )
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

    def _source_identity(self, repository_root: Path, base_commit: str) -> str:
        """Hash the complete tracked destination state relative to its frozen base."""
        return _sha256(
            self._git_ok(
                repository_root,
                ["diff", "--binary", base_commit],
                code="integration_source_identity_failed",
            )
        )

    def _freeze_integration_commit(
        self,
        repository_root: Path,
        *,
        base_commit: str,
        queue_id: str,
        source_identity: str,
    ) -> str:
        """Create an immutable commit/ref for the gated index without moving HEAD."""
        tree = self._git_ok(repository_root, ["write-tree"], code="integration_tree_freeze_failed").decode().strip()
        frozen_diff = self._git_ok(repository_root, ["diff", "--binary", base_commit, tree], code="integration_tree_verify_failed")
        if _sha256(frozen_diff) != source_identity:
            raise TodoError("integration_tree_mismatch", "Frozen integration tree differs from the gated source")
        commit = self._git_input_ok(
            repository_root,
            ["commit-tree", tree, "-p", base_commit],
            f"coding-workflow integration {queue_id}\n".encode("utf-8"),
            code="integration_commit_freeze_failed",
        ).decode().strip()
        self._git_ok(
            repository_root,
            ["update-ref", f"refs/coding-workflow/integrations/{queue_id}", commit],
            code="integration_ref_freeze_failed",
        )
        return commit

    def _advance_integration_head(self, repository_root: Path, frozen_commit: str) -> None:
        """Advance only the managed destination ref; its index/tree already match."""
        previous = self._commit(repository_root, "HEAD")
        self._git_ok(
            repository_root,
            ["update-ref", "HEAD", frozen_commit, previous],
            code="integration_head_advance_failed",
        )
        if self._commit(repository_root, "HEAD") != frozen_commit:
            raise TodoError("integration_head_advance_failed", "Managed destination did not advance to the frozen integration commit")
        if self._git_ok(repository_root, ["status", "--porcelain=v1", "-z"], code="integration_status_failed"):
            raise TodoError("integration_head_state_mismatch", "Managed destination does not exactly match the frozen integration commit")

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
        if mode != "read_shared" and self.repository_identity_resolver is None:
            raise TodoError("repository_identity_resolver_required", "Writable workspaces require an authoritative repository identity resolver")
        if self.repository_identity_resolver is not None:
            authoritative_identity = self.repository_identity_resolver(repository_root)
            if repository_identity != authoritative_identity:
                raise TodoError("repository_identity_mismatch", "Workspace repository identity is not authoritative")
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

        def reserve(conn: Any, revision: int) -> dict[str, object]:
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
                    str(target) if target else None, branch, "provisioning", integration_task_id, now, now,
                ),
            )
            return {"workspace_id": workspace_id, "run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base}

        def activate(conn: Any, rev: int) -> dict[str, object]:
            changed = conn.execute(
                "UPDATE workflow_workspaces SET state='active',updated_at=? WHERE id=? AND state='provisioning'",
                (utc_now(), workspace_id),
            )
            if changed.rowcount != 1:
                raise TodoError("workspace_provisioning_state_changed", "Workspace reservation changed during materialization")
            return {"workspace_id": workspace_id, "run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_workspace",
            entity_id=workspace_id,
            event_type="workflow_workspace_reserved",
            payload={"run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base},
            operation=reserve,
        )
        try:
            if target is not None:
                target.parent.mkdir(parents=True, exist_ok=True)
                args = ["worktree", "add"]
                if branch:
                    args.extend(["-b", branch])
                else:
                    args.append("--detach")
                args.extend([str(target), canonical_base])
                self._git_ok(repository_root, args, code="workspace_materialization_failed")
        except Exception:
            self.db.mutate(
                actor_session_id=actor_session_id,
                entity_type="workflow_workspace",
                entity_id=workspace_id,
                event_type="workflow_workspace_provisioning_failed",
                payload={"preserved": True},
                operation=lambda conn, rev: conn.execute(
                    "UPDATE workflow_workspaces SET state='provisioning_failed',updated_at=? WHERE id=?",
                    (utc_now(), workspace_id),
                ),
            )
            raise

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_workspace",
            entity_id=workspace_id,
            event_type="workflow_workspace_created",
            payload={"run_id": run_id, "lane_id": lane_id, "mode": mode, "base_commit": canonical_base},
            operation=activate,
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
            if not conn.execute(
                "SELECT 1 FROM workflow_lane_tasks WHERE lane_id=? AND task_id=?",
                (workspace["lane_id"], task_id),
            ).fetchone():
                raise TodoError("workspace_artifact_task_mismatch", "Artifact task is not assigned to the producer lane")
            root = Path(workspace["worktree_path"])
            base = workspace["base_commit"]
        if kind == "commit":
            resolved = self._commit(root, artifact_ref)
            if resolved != self._commit(root, "HEAD"):
                raise TodoError("artifact_workspace_head_mismatch", "Commit artifact must be the registered workspace HEAD")
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
            digest = _sha256(content)
            artifact_dir = self.managed_root / "artifacts"
            artifact_dir.mkdir(parents=True, exist_ok=True)
            immutable = artifact_dir / f"{digest}.patch"
            _write_immutable(immutable, content)
            artifact_ref = str(immutable)
        digest = _sha256(content)
        artifact_id = str(uuid.uuid4())
        now = utc_now()

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state,base_commit,lane_id FROM workflow_workspaces WHERE id=?", (workspace_id,)).fetchone()
            if current is None or current["state"] not in {"active", "artifact_ready"}:
                raise TodoError("workspace_artifact_state", "Workspace is not eligible to publish an artifact")
            if not conn.execute(
                "SELECT 1 FROM workflow_lane_tasks WHERE lane_id=? AND task_id=?",
                (current["lane_id"], task_id),
            ).fetchone():
                raise TodoError("workspace_artifact_task_mismatch", "Artifact task ownership changed")
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
            if destination["integration_task_id"] != integration_task_id or not conn.execute(
                "SELECT 1 FROM workflow_lane_tasks WHERE lane_id=? AND task_id=?",
                (integrator_lane_id, integration_task_id),
            ).fetchone():
                raise TodoError("integration_task_owner_mismatch", "Integration task is not declared for the integrator workspace and lane")
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
        def reserve(conn: Any, revision: int) -> dict[str, object]:
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
            conn.execute(
                "UPDATE workflow_integration_queue SET state='applying',updated_at=? WHERE id=? AND state='queued'",
                (utc_now(), queue_id),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state='applying',updated_at=? WHERE run_id=? AND lane_id=?",
                (utc_now(), row["run_id"], row["integrator_lane_id"]),
            )
            return dict(row)

        row, _ = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_integration_reserved",
            payload={"state": "applying"},
            operation=reserve,
        )
        destination = Path(row["destination_path"])
        try:
            if not destination.exists():
                raise TodoError("integration_workspace_missing", "Destination integration workspace is unavailable")
            status = self._git_ok(destination, ["status", "--porcelain=v1", "-z"], code="integration_status_failed")
            if status:
                raise TodoError("integration_workspace_dirty", "Destination has dirty changes; all files are preserved")
            pre_apply_head = self._commit(destination, "HEAD")
            if row["kind"] == "commit":
                current = self._commit(destination, row["artifact_ref"])
                diff = self._git_ok(destination, ["diff", "--binary", row["base_commit"], current], code="artifact_diff_failed")
                if _sha256(diff) != row["content_hash"]:
                    raise TodoError("artifact_content_changed", "Commit artifact no longer matches its immutable hash")
                command = ["cherry-pick", "--no-commit", f"{row['base_commit']}..{current}"]
            else:
                patch = Path(row["artifact_ref"])
                content = patch.read_bytes() if patch.is_file() else b""
                if _sha256(content) != row["content_hash"]:
                    raise TodoError("artifact_content_changed", "Patch artifact no longer matches its immutable hash")
                command = ["apply", "--index", "--3way", str(patch)]
            applied = self._git(destination, command)
        except Exception as exc:
            code = exc.code if isinstance(exc, TodoError) else "integration_apply_exception"
            def fail_operation(conn: Any, revision: int) -> None:
                conn.execute(
                    "UPDATE workflow_integration_queue SET state='apply_failed',conflict_json=?,updated_at=? WHERE id=? AND state='applying'",
                    (_json({"code": code, "preserved": True}), utc_now(), queue_id),
                )
                conn.execute(
                    "UPDATE workflow_workspaces SET state='apply_failed',updated_at=? WHERE run_id=? AND lane_id=? AND state='applying'",
                    (utc_now(), row["run_id"], row["integrator_lane_id"]),
                )
            self.db.mutate(
                actor_session_id=actor_session_id,
                entity_type="workflow_integration_queue",
                entity_id=queue_id,
                event_type="workflow_integration_apply_failed",
                payload={"code": code, "preserved": True},
                operation=fail_operation,
            )
            raise
        conflicts: list[str] = []
        if applied.returncode != 0:
            unresolved = self._git(destination, ["diff", "--name-only", "--diff-filter=U"])
            conflicts = sorted(filter(None, unresolved.stdout.decode("utf-8", errors="replace").splitlines()))
        now = utc_now()
        state = "awaiting_gates" if applied.returncode == 0 else "conflict"
        source_identity = self._source_identity(destination, row["base_commit"]) if applied.returncode == 0 else None
        conflict = {
            "paths": conflicts,
            "integration_task_id": row["integration_task_id"],
            "preserved": applied.returncode != 0,
        } if applied.returncode != 0 else {}

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state FROM workflow_integration_queue WHERE id=?", (queue_id,)).fetchone()
            if current is None or current["state"] != "applying":
                raise TodoError("integration_state_changed", "Integration queue entry changed while Git was applying")
            merge_result = {
                "returncode": applied.returncode,
                "state": state,
                "apply_revision": revision,
                "pre_apply_head": pre_apply_head,
                "source_identity": source_identity,
                "destination_worktree": str(destination.resolve()),
            }
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

    def retry_conflict(self, *, queue_id: str, actor_session_id: str | None = None) -> dict[str, object]:
        """Restore a preserved cherry-pick conflict to its recorded base for one explicit retry."""

        with self.db.read() as conn:
            row = conn.execute(
                "SELECT q.state,q.position,q.run_id,q.integrator_lane_id,q.merge_result_json,a.base_commit,d.worktree_path "
                "FROM workflow_integration_queue q "
                "JOIN workflow_patch_artifacts a ON a.id=q.patch_artifact_id "
                "JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id "
                "WHERE q.id=?",
                (queue_id,),
            ).fetchone()
        if row is None or row["state"] != "conflict":
            raise TodoError("integration_conflict_required", "Only a preserved integration conflict can be retried")
        merge_result = json.loads(row["merge_result_json"] or "{}")
        pre_apply_head = str(merge_result.get("pre_apply_head") or (row["base_commit"] if int(row["position"]) == 0 else ""))
        if not pre_apply_head:
            raise TodoError("integration_conflict_provenance_missing", "Conflict retry requires the recorded pre-apply commit")
        destination = Path(row["worktree_path"])
        aborted = self._git(destination, ["cherry-pick", "--abort"])
        if aborted.returncode != 0:
            # Older --no-commit integrations may leave an unmerged index
            # without a sequencer record.  The destination was proven clean
            # immediately before apply, so restoring the recorded pre-apply
            # tree is the only bounded fallback; untracked residue still makes
            # the subsequent cleanliness check fail closed.
            restored = self._git(
                destination,
                ["restore", "--source", pre_apply_head, "--staged", "--worktree", "--", "."],
            )
            if restored.returncode != 0:
                raise TodoError("integration_conflict_abort_failed", "Preserved conflict could not be restored safely")
        if self._git_ok(destination, ["status", "--porcelain=v1", "-z"], code="integration_status_failed"):
            raise TodoError("integration_conflict_restore_dirty", "Conflict restoration did not produce a clean destination")
        if self._commit(destination, "HEAD") != pre_apply_head:
            raise TodoError("integration_conflict_restore_mismatch", "Conflict restoration did not return to the recorded pre-apply commit")

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state FROM workflow_integration_queue WHERE id=?", (queue_id,)).fetchone()
            if current is None or current["state"] != "conflict":
                raise TodoError("integration_state_changed", "Integration conflict changed during restoration")
            conn.execute(
                "UPDATE workflow_integration_queue SET state='queued',conflict_json='{}',merge_result_json='{}',updated_at=? WHERE id=?",
                (utc_now(), queue_id),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state='active',merge_result_json='{}',updated_at=? WHERE run_id=? AND lane_id=?",
                (utc_now(), row["run_id"], row["integrator_lane_id"]),
            )
            return {"queue_id": queue_id, "state": "queued", "restored_head": pre_apply_head}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_integration_conflict_retried",
            payload={"restored_head": pre_apply_head},
            operation=operation,
        )
        result["revision"] = revision
        return result

    def retry_failed_gates(self, *, queue_id: str, actor_session_id: str | None = None) -> dict[str, object]:
        """Reopen preserved applied source after a corrected gate contract."""

        with self.db.read() as conn:
            row = conn.execute(
                "SELECT q.state,q.run_id,q.integrator_lane_id,q.merge_result_json,a.base_commit,d.worktree_path "
                "FROM workflow_integration_queue q "
                "JOIN workflow_patch_artifacts a ON a.id=q.patch_artifact_id "
                "JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id "
                "WHERE q.id=?",
                (queue_id,),
            ).fetchone()
        if row is None or row["state"] != "gate_failed":
            raise TodoError("integration_gate_failure_required", "Only a preserved gate failure can be retried")
        merge_result = json.loads(row["merge_result_json"] or "{}")
        source_identity = str(merge_result.get("source_identity") or "")
        destination = Path(row["worktree_path"])
        if not source_identity or self._source_identity(destination, str(row["base_commit"])) != source_identity:
            raise TodoError("integration_source_changed", "Preserved gate-failed source changed before retry")

        def operation(conn: Any, revision: int) -> dict[str, object]:
            current = conn.execute("SELECT state FROM workflow_integration_queue WHERE id=?", (queue_id,)).fetchone()
            if current is None or current["state"] != "gate_failed":
                raise TodoError("integration_state_changed", "Gate-failed integration changed during retry")
            conn.execute(
                "UPDATE workflow_integration_queue SET state='awaiting_gates',merge_result_json=?,updated_at=? WHERE id=?",
                (_json({
                    "state": "awaiting_gates",
                    "apply_revision": revision,
                    "source_identity": source_identity,
                    "destination_worktree": str(destination.resolve()),
                    "gate_retry": True,
                }), utc_now(), queue_id),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state='awaiting_gates',updated_at=? WHERE run_id=? AND lane_id=?",
                (utc_now(), row["run_id"], row["integrator_lane_id"]),
            )
            return {"queue_id": queue_id, "state": "awaiting_gates", "source_identity": source_identity}

        result, revision = self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_integration_gates_retried",
            payload={"source_identity": source_identity},
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
        authoritative: list[dict[str, object]] = []
        with self.db.read() as conn:
            queue = conn.execute(
                "SELECT q.integration_task_id,q.updated_at,q.state,q.merge_result_json,d.worktree_path,d.base_commit FROM workflow_integration_queue q "
                "JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id WHERE q.id=?",
                (queue_id,),
            ).fetchone()
            if queue is None:
                raise TodoError("integration_queue_missing", "Integration queue entry does not exist")
            if queue["state"] != "awaiting_gates":
                raise TodoError("integration_not_awaiting_gates", "Integration is not awaiting post-merge gates")
            applied = json.loads(queue["merge_result_json"] or "{}")
            apply_revision = int(applied.get("apply_revision", 0))
            source_identity = str(applied.get("source_identity", ""))
            destination_path = str(Path(queue["worktree_path"]).resolve())
            if not apply_revision or not source_identity or applied.get("destination_worktree") != destination_path:
                raise TodoError("integration_apply_provenance_missing", "Integration apply provenance is incomplete")
            if self._source_identity(Path(destination_path), queue["base_commit"]) != source_identity:
                raise TodoError("integration_source_changed", "Destination source changed after integration apply")
            required_gate_ids = {
                row[0] for row in conn.execute(
                    "SELECT id FROM gates WHERE task_id=? AND required=1", (queue["integration_task_id"],)
                )
            }
            supplied_gate_ids = {str(item.get("gate_id", "")) for item in gate_results}
            if not required_gate_ids or supplied_gate_ids != required_gate_ids:
                raise TodoError("integration_gate_coverage_incomplete", "All and only required integration-task gates must be supplied")
            for supplied in gate_results:
                gate_id = str(supplied.get("gate_id", ""))
                evidence_id = str(supplied.get("evidence_id", ""))
                row = conn.execute(
                    "SELECT g.id,g.task_id,g.status,g.valid,g.input_fingerprint,e.id AS evidence_id,e.status AS evidence_status,e.revision,e.created_at,e.metadata_json "
                    "FROM gates g JOIN evidence e ON e.gate_id=g.id WHERE g.id=? AND e.id=?",
                    (gate_id, evidence_id),
                ).fetchone()
                if not row or row["task_id"] != queue["integration_task_id"]:
                    raise TodoError("integration_gate_provenance_invalid", "Post-merge gate evidence is not authoritative for the integration task")
                metadata = json.loads(row["metadata_json"] or "{}")
                if metadata.get("input_fingerprint") != row["input_fingerprint"]:
                    raise TodoError("integration_gate_provenance_stale", "Gate evidence does not match the current gate input fingerprint")
                if (
                    int(metadata.get("started_revision", -1)) < apply_revision
                    or metadata.get("workspace_path") != destination_path
                    or metadata.get("source_identity") != source_identity
                ):
                    raise TodoError(
                        "integration_gate_workspace_mismatch",
                        "Post-merge gate did not start against the applied destination source",
                    )
                authoritative.append({
                    "gate_id": gate_id,
                    "evidence_id": evidence_id,
                    "status": row["status"],
                    "valid": bool(row["valid"]),
                    "evidence_status": row["evidence_status"],
                    "evidence_revision": int(row["revision"]),
                    "input_fingerprint": row["input_fingerprint"],
                    "started_revision": int(metadata["started_revision"]),
                })
        passed = all(item["status"] == "passed" and item["valid"] and item["evidence_status"] == "passed" for item in authoritative)
        now = utc_now()
        target_state = "integrated" if passed else "gate_failed"
        reserved = False

        def reserve_finalization(conn: Any, revision: int) -> dict[str, object]:
            row = conn.execute(
                "SELECT q.state,q.run_id,q.integrator_lane_id,q.integration_task_id,q.merge_result_json "
                "FROM workflow_integration_queue q WHERE q.id=?",
                (queue_id,),
            ).fetchone()
            if row is None or row["state"] != "awaiting_gates":
                raise TodoError("integration_not_awaiting_gates", "Integration is not awaiting post-merge gates")
            current_apply = json.loads(row["merge_result_json"] or "{}")
            if int(current_apply.get("apply_revision", 0)) != apply_revision or current_apply.get("source_identity") != source_identity:
                raise TodoError("integration_apply_provenance_changed", "Integration apply provenance changed before finalization")
            required_gate_ids = {
                item[0] for item in conn.execute(
                    "SELECT id FROM gates WHERE task_id=? AND required=1", (row["integration_task_id"],)
                )
            }
            if required_gate_ids != {str(item["gate_id"]) for item in authoritative}:
                raise TodoError("integration_gate_coverage_changed", "Required integration gates changed during finalization")
            conn.execute(
                "UPDATE workflow_integration_queue SET state='finalizing',updated_at=? WHERE id=? AND state='awaiting_gates'",
                (utc_now(), queue_id),
            )
            conn.execute(
                "UPDATE workflow_workspaces SET state='finalizing',updated_at=? WHERE run_id=? AND lane_id=?",
                (utc_now(), row["run_id"], row["integrator_lane_id"]),
            )
            return {"queue_id": queue_id, "state": "finalizing"}

        self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_integration_queue",
            entity_id=queue_id,
            event_type="workflow_integration_finalization_reserved",
            payload={"source_identity": source_identity, "gate_count": len(authoritative)},
            operation=reserve_finalization,
        )
        reserved = True
        integrated_artifact: dict[str, object] | None = None
        destination = Path(queue["worktree_path"])
        try:
            if self._source_identity(destination, queue["base_commit"]) != source_identity:
                raise TodoError("integration_source_changed", "Destination source changed during finalization")
            if passed:
                content = self._git_ok(destination, ["diff", "--binary", queue["base_commit"]], code="integration_final_diff_failed")
                digest = _sha256(content)
                if digest != source_identity:
                    raise TodoError("integration_source_changed", "Final artifact does not match the gated destination source")
                artifact_dir = self.managed_root / "artifacts"
                artifact_dir.mkdir(parents=True, exist_ok=True)
                artifact_path = artifact_dir / f"integration-{digest}.patch"
                _write_immutable(artifact_path, content)
                frozen_commit = self._freeze_integration_commit(
                    destination,
                    base_commit=queue["base_commit"],
                    queue_id=queue_id,
                    source_identity=source_identity,
                )
                self._advance_integration_head(destination, frozen_commit)
                integrated_artifact = {
                    "kind": "commit",
                    "ref": frozen_commit,
                    "patch_ref": str(artifact_path),
                    "content_hash": digest,
                }

            def operation(conn: Any, revision: int) -> dict[str, object]:
                row = conn.execute(
                    """SELECT q.*,a.workspace_id,d.id AS destination_workspace_id FROM workflow_integration_queue q
                       JOIN workflow_patch_artifacts a ON a.id=q.patch_artifact_id
                       JOIN workflow_workspaces d ON d.run_id=q.run_id AND d.lane_id=q.integrator_lane_id
                       WHERE q.id=?""",
                    (queue_id,),
                ).fetchone()
                if row is None or row["state"] != "finalizing":
                    raise TodoError("integration_not_finalizing", "Integration finalization reservation was lost")
                for gate in authoritative:
                    current = conn.execute(
                        "SELECT g.status,g.valid,g.input_fingerprint,e.status,e.metadata_json,e.revision "
                        "FROM gates g JOIN evidence e ON e.gate_id=g.id WHERE g.id=? AND e.id=?",
                        (gate["gate_id"], gate["evidence_id"]),
                    ).fetchone()
                    metadata = json.loads(current["metadata_json"] or "{}") if current else {}
                    if (
                        not current
                        or current["status"] != gate["status"]
                        or bool(current["valid"]) != gate["valid"]
                        or current["status"] != current[3]
                        or int(current["revision"]) != gate["evidence_revision"]
                        or metadata.get("input_fingerprint") != current["input_fingerprint"]
                        or int(metadata.get("started_revision", -1)) < apply_revision
                        or metadata.get("workspace_path") != destination_path
                        or metadata.get("source_identity") != source_identity
                    ):
                        raise TodoError("integration_gate_provenance_stale", "Integration gate provenance changed before finalization")
                if self._source_identity(destination, queue["base_commit"]) != source_identity:
                    raise TodoError("integration_source_changed", "Destination source changed before authoritative finalization")
                if integrated_artifact:
                    frozen = self._git_ok(
                        destination,
                        ["diff", "--binary", queue["base_commit"], str(integrated_artifact["ref"])],
                        code="integration_frozen_commit_missing",
                    )
                    if _sha256(frozen) != source_identity:
                        raise TodoError("integration_frozen_commit_changed", "Frozen integration commit no longer matches gated source")
                merge_result = {"state": target_state, "gates": authoritative, "integrated_artifact": integrated_artifact, "source_identity": source_identity}
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
                if integrated_artifact:
                    final_artifact_id = str(uuid.uuid4())
                    conn.execute(
                        "INSERT INTO workflow_patch_artifacts(id,workspace_id,task_id,kind,artifact_ref,content_hash,base_commit,created_at,state) "
                        "VALUES(?,?,?,?,?,?,?,?, 'integrated')",
                        (final_artifact_id, row["destination_workspace_id"], row["integration_task_id"], integrated_artifact["kind"], integrated_artifact["ref"], integrated_artifact["content_hash"], queue["base_commit"], now),
                    )
                    conn.execute(
                        "UPDATE workflow_workspaces SET artifact_kind=?,artifact_ref=?,diff_hash=? WHERE run_id=? AND lane_id=?",
                        (integrated_artifact["kind"], integrated_artifact["ref"], integrated_artifact["content_hash"], row["run_id"], row["integrator_lane_id"]),
                    )
                return {"queue_id": queue_id, "state": target_state, "gates": authoritative, "integrated_artifact": integrated_artifact}

            result, revision = self.db.mutate(
                actor_session_id=actor_session_id,
                entity_type="workflow_integration_queue",
                entity_id=queue_id,
                event_type="workflow_post_merge_gates_recorded",
                payload={"state": target_state, "gate_count": len(gate_results), "source_identity": source_identity},
                operation=operation,
            )
        except Exception:
            if reserved:
                self.db.mutate(
                    actor_session_id=actor_session_id,
                    entity_type="workflow_integration_queue",
                    entity_id=queue_id,
                    event_type="workflow_integration_finalization_failed",
                    payload={"preserved": True},
                    operation=lambda conn, revision: (
                        conn.execute("UPDATE workflow_integration_queue SET state='finalization_failed',updated_at=? WHERE id=? AND state='finalizing'", (utc_now(), queue_id)),
                        conn.execute("UPDATE workflow_workspaces SET state='finalization_failed',updated_at=? WHERE run_id=(SELECT run_id FROM workflow_integration_queue WHERE id=?) AND lane_id=(SELECT integrator_lane_id FROM workflow_integration_queue WHERE id=?) AND state='finalizing'", (utc_now(), queue_id, queue_id)),
                    ),
                )
            raise
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
            if conn.execute(
                "SELECT 1 FROM workflow_dispatches WHERE workspace_id=? AND state='active'", (workspace_id,)
            ).fetchone():
                raise TodoError("workspace_cleanup_owner_active", "Active workspace owner must stop before cleanup eligibility")
            if path is not None and self._git_ok(path, ["status", "--porcelain=v1", "-z"], code="workspace_status_failed"):
                raise TodoError("workspace_dirty_preserved", "Workspace became dirty during cleanup assessment")
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
