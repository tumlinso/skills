"""Canonical in-process coding-workflow service over todo semantic authority."""

from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from ..child_execution import (
    authorize_child_execution_for_claim,
    child_execution_status_for_claim,
    disposition_child_execution_for_claim,
)
from ..claims import claim_best, release_claim_id, sweep_expired
from ..config import utc_now
from ..evidence import required_gates
from ..gates import run_gate
from ..interfaces import freeze as freeze_interface
from ..interfaces import revise as revise_interface
from ..models import ExitCode, TodoError
from ..ownership import scopes_for
from ..readiness import explain_task
from ..service import Service
from ..sessions import create_session
from .capabilities import (
    AuthorizedCapability,
    WorkflowCapabilityLocator,
    WorkflowCapabilityStore,
    child_operations,
    default_first_class_operations,
)
from .context_fragments import ContextFragmentStore, compose_child_packet
from .foundation import CapabilityLineage, CHILD_RESULT_KINDS, content_hash, require_bounded_payload
from .lanes import (
    advance_lane_in_transaction,
    create_lane_in_transaction,
    deterministic_lane_assignment,
    dispatch_claim_in_transaction,
    enqueue_tasks_in_transaction,
)
from .messages import MessageService
from .rendezvous import RendezvousService
from .roles import require_role_action
from .runs import RunService


ServiceFactory = Callable[[str | Path], Service]


def repository_identity(repo_root: Path, project_uuid: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-common-dir"],
        capture_output=True,
        text=True,
        check=False,
    )
    common = result.stdout.strip() if result.returncode == 0 else str(repo_root)
    candidate = Path(common)
    if not candidate.is_absolute():
        candidate = (repo_root / candidate).resolve()
    return hashlib.sha256(f"{project_uuid}\0{candidate}".encode()).hexdigest()


class WorkflowKernel:
    """One semantic service shared by the todo CLI and coding-workflow MCP."""

    def __init__(
        self,
        *,
        service_factory: ServiceFactory = Service,
        locator: WorkflowCapabilityLocator | None = None,
        ctxpp_adapter: Any | None = None,
        local_worker_adapter: Any | None = None,
    ):
        self.service_factory = service_factory
        self.locator = locator or WorkflowCapabilityLocator()
        self.ctxpp_adapter = ctxpp_adapter
        self.local_worker_adapter = local_worker_adapter

    def _service(self, repo_root: str | Path, *, bootstrap: bool = False) -> Service:
        root = Path(repo_root).resolve()
        try:
            return self.service_factory(root)
        except TodoError as exc:
            if bootstrap and exc.code == "project_not_bootstrapped":
                return Service(root, bootstrap=True)
            raise

    def _resolve_service(self, capability: AuthorizedCapability) -> Service:
        # A locator contains no lineage semantics, only a hash -> repository hint.
        for hint in self.locator.root.glob("*"):
            try:
                repo = Path(hint.read_text(encoding="utf-8").strip()).resolve()
                service = self._service(repo)
                with service.db.read() as conn:
                    row = conn.execute("SELECT 1 FROM workflow_capabilities WHERE id=?", (capability.id,)).fetchone()
                if row:
                    return service
            except (OSError, TodoError):
                continue
        raise TodoError("invalid_workflow_capability", "Capability project is no longer locatable")

    @staticmethod
    def _context_version(conn: Any, run_id: str, lane_id: str, task_id: str) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(version),1) FROM workflow_context_fragments WHERE run_id=? "
            "AND (lane_id IS NULL OR lane_id=?) AND (task_id IS NULL OR task_id=?) AND invalidated_at IS NULL",
            (run_id, lane_id, task_id),
        ).fetchone()
        return max(1, int(row[0]))

    @staticmethod
    def _session(conn: Any, repo_root: Path) -> Any:
        external = os.environ.get("CODEX_THREAD_ID") or os.environ.get("OPENAI_CODEX_THREAD_ID")
        if external:
            row = conn.execute(
                "SELECT * FROM sessions WHERE external_id=? AND repo_root=? AND state='active' ORDER BY last_seen_at DESC LIMIT 1",
                (external, str(repo_root)),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM sessions WHERE hostname=? AND pid=? AND repo_root=? AND state='active' ORDER BY last_seen_at DESC LIMIT 1",
                (socket.gethostname(), os.getpid(), str(repo_root)),
            ).fetchone()
        return row

    def next_task(self, *, repo_root: str, task_id: str | None) -> Mapping[str, Any]:
        service = self._service(repo_root, bootstrap=True)
        capabilities = WorkflowCapabilityStore(service.db)
        project_uuid = str(service.project["project_uuid"])
        repo_identity = repository_identity(service.paths.repo_root, project_uuid)

        def operation(conn: Any, revision: int) -> dict[str, Any]:
            sweep_expired(conn, service.paths.repo_root)
            session = self._session(conn, service.paths.repo_root)
            if session:
                resumed = conn.execute(
                    "SELECT d.*,l.run_id,l.role,lt.task_id FROM workflow_dispatches d "
                    "JOIN workflow_lanes l ON l.id=d.lane_id "
                    "JOIN workflow_lane_tasks lt ON lt.lane_id=d.lane_id AND lt.state='active' "
                    "JOIN claims c ON c.id=d.claim_id AND c.state='active' "
                    "WHERE d.session_id=? AND d.state='active' ORDER BY d.created_at DESC LIMIT 1",
                    (session["id"],),
                ).fetchone()
                if resumed and (task_id is None or resumed["task_id"] == task_id):
                    now = utc_now()
                    conn.execute("UPDATE sessions SET last_seen_at=? WHERE id=?", (now, session["id"]))
                    conn.execute("UPDATE claims SET heartbeat_at=? WHERE id=?", (now, resumed["claim_id"]))
                    conn.execute("UPDATE workflow_dispatches SET heartbeat_at=?,revision=? WHERE id=?", (now, revision, resumed["id"]))
                    lineage = CapabilityLineage(
                        "first_class", project_uuid, repo_identity, str(session["id"]),
                        str(resumed["claim_id"]), str(resumed["run_id"]), str(resumed["lane_id"]),
                        str(resumed["role"]), str(resumed["task_id"]),
                        default_first_class_operations(str(resumed["role"])), 1,
                    )
                    handle, authorized = capabilities.stage_first_class(conn, lineage=lineage, revision=revision)
                    return {
                        "status": "resumed", "workflow_handle": handle,
                        "run_id": resumed["run_id"], "lane_id": resumed["lane_id"],
                        "role": resumed["role"], "task_id": resumed["task_id"],
                        "context_version": int(resumed["context_version"]),
                        "capability_id": authorized.id,
                    }
            else:
                session_view, _raw_session_token = create_session(
                    conn, service.paths.repo_root, {"command": "workflow.next_task", "owner_system": "coding-workflow"}
                )
                session = conn.execute("SELECT * FROM sessions WHERE id=?", (session_view["agent_id"],)).fetchone()

            runs = conn.execute("SELECT id FROM workflow_runs WHERE status='active' ORDER BY created_at,id").fetchall()
            if not runs:
                raise TodoError("workflow_run_missing", "No active workflow run is available")
            selected = None
            selected_run = None
            if task_id:
                row = conn.execute(
                    "SELECT l.run_id,l.id AS lane_id,l.role,lt.task_id FROM workflow_lane_tasks lt "
                    "JOIN workflow_lanes l ON l.id=lt.lane_id JOIN workflow_runs r ON r.id=l.run_id "
                    "WHERE lt.task_id=? AND lt.state='queued' AND r.status='active' ORDER BY l.run_id,l.id LIMIT 1",
                    (task_id,),
                ).fetchone()
                if row:
                    selected = dict(row)
                    selected_run = str(row["run_id"])
            else:
                for run in runs:
                    candidate = deterministic_lane_assignment(conn, str(run["id"]))
                    if candidate:
                        selected, selected_run = candidate, str(run["id"])
                        break
            if not selected or not selected_run:
                raise TodoError("no_actionable_work", "No safe first-class lane is claimable", ExitCode.NO_ACTIONABLE_WORK)
            claim, _raw_claim_token = claim_best(
                conn, service.paths.repo_root, str(session["id"]), revision,
                service.claim_lease_seconds, requested_task_id=str(selected["task_id"]),
                reconcile_expired=False, owner_system="coding-workflow",
                owner_instance_id="fi_" + uuid.uuid4().hex,
            )
            context_version = self._context_version(conn, selected_run, str(selected["lane_id"]), str(selected["task_id"]))
            dispatch = dispatch_claim_in_transaction(
                conn, revision, run_id=selected_run, lane_id=str(selected["lane_id"]),
                session_id=str(session["id"]), claim_id=str(claim["claim_id"]),
                context_version=context_version, hostname=socket.gethostname(), pid=os.getpid(),
            )
            lineage = CapabilityLineage(
                "first_class", project_uuid, repo_identity, str(session["id"]), str(claim["claim_id"]),
                selected_run, str(selected["lane_id"]), str(selected["role"]), str(selected["task_id"]),
                default_first_class_operations(str(selected["role"])), 1,
            )
            handle, authorized = capabilities.stage_first_class(conn, lineage=lineage, revision=revision)
            return {**dispatch, "workflow_handle": handle, "capability_id": authorized.id}

        try:
            result, revision, _ = service.mutate(
                actor=lambda value: value.get("session_id"), entity_type="workflow_dispatch",
                entity_id=lambda value: value.get("lane_id"), event_type="workflow.next_task",
                payload=lambda value: {key: value.get(key) for key in ("run_id", "lane_id", "task_id", "status")},
                operation=operation,
            )
        except TodoError as exc:
            if exc.code in {"no_actionable_work", "workflow_run_missing"}:
                return {"status": "idle", "warnings": [exc.code], "recommended_next_call": "next_task"}
            raise
        handle = str(result["workflow_handle"])
        self.locator.register(handle, service.paths.repo_root)
        context = ContextFragmentStore(service.db).compose_first_class(
            run_id=str(result["run_id"]), lane_id=str(result["lane_id"]), task_id=str(result["task_id"])
        )
        return {
            **result,
            "project_revision": revision,
            "context": context,
            "allowed_actions": ["inspect_task", "coordinate_task", "delegate_task", "finish_task"],
            "recommended_next_call": "inspect_task",
        }

    def inspect_task(self, capability: AuthorizedCapability, *, kind: str, target: str | None, budget_bytes: int) -> Mapping[str, Any]:
        service = self._resolve_service(capability)
        lineage = capability.lineage
        with service.db.read() as conn:
            if kind == "task":
                payload: dict[str, Any] = {
                    "task": explain_task(conn, target or lineage.task_id),
                    "scopes": scopes_for(conn, lineage.task_id),
                }
            elif kind == "evidence":
                payload = {"evidence": [dict(row) for row in conn.execute(
                    "SELECT id,task_id,gate_id,kind,path,content_hash,created_at,revision FROM evidence WHERE task_id=? ORDER BY revision DESC LIMIT 50",
                    (target or lineage.task_id,),
                )]}
            elif kind == "run":
                payload = RunService(service.db).inspect(target or str(lineage.run_id))
            elif kind == "lane":
                lane_id = target or str(lineage.lane_id)
                lane = conn.execute("SELECT * FROM workflow_lanes WHERE id=? AND run_id=?", (lane_id, lineage.run_id)).fetchone()
                payload = {"lane": dict(lane) if lane else None, "queue": [dict(row) for row in conn.execute(
                    "SELECT * FROM workflow_lane_tasks WHERE lane_id=? ORDER BY position", (lane_id,),
                )]}
            elif kind == "decision":
                payload = {"decisions": [dict(row) for row in conn.execute("SELECT * FROM decisions ORDER BY id LIMIT 100")]}
            elif kind == "messages":
                payload = MessageService(service.db).inspect(run_id=str(lineage.run_id), lane_id=str(lineage.lane_id), limit=50)
            elif kind == "rendezvous":
                if target:
                    payload = RendezvousService(service.db).inspect(target)
                else:
                    payload = {"rendezvous": [dict(row) for row in conn.execute(
                        "SELECT id,run_id,barrier_id,mode,quorum,join_task_id,state,revision FROM workflow_rendezvous WHERE run_id=? ORDER BY id",
                        (lineage.run_id,),
                    )]}
            elif kind == "workspace":
                payload = {"workspaces": [dict(row) for row in conn.execute(
                    "SELECT * FROM workflow_workspaces WHERE run_id=? AND (? IS NULL OR id=?) ORDER BY id",
                    (lineage.run_id, target, target),
                )]}
            elif kind == "integration":
                payload = {"integration_queue": [dict(row) for row in conn.execute(
                    "SELECT * FROM workflow_integration_queue WHERE run_id=? ORDER BY integration_task_id,position",
                    (lineage.run_id,),
                )]}
            elif kind == "source":
                payload = {}
            else:
                raise TodoError("invalid_inspection_kind", "Inspection kind is unsupported")
        if kind == "source":
            if self.ctxpp_adapter is None:
                payload = {
                    "status": "fallback_authorized",
                    "fallback_authorization": {
                        "specialized_skill": "cpp-context-compiler", "permitted_operation": "bounded source inspection",
                        "reason": "ctxpp adapter is unavailable", "scope": {"task_id": lineage.task_id, "target": target},
                        "access": "read_only",
                    },
                }
            else:
                payload = dict(self.ctxpp_adapter.inspect(repo=service.paths.repo_root, target=target, budget_bytes=budget_bytes))
        require_bounded_payload(payload, limit=budget_bytes, code="workflow_inspection_too_large")
        return payload

    def coordinate_task(self, capability: AuthorizedCapability, *, action: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        service = self._resolve_service(capability)
        lineage = capability.lineage
        role_action = {"publish_interface": "publish_interface", "request_integration": "request_integration"}.get(action, action)
        require_role_action(str(lineage.role), role_action)
        if action == "sync":
            return MessageService(service.db).sync(
                capability_class="first_class", run_id=str(lineage.run_id), lane_id=str(lineage.lane_id),
                actor_session_id=lineage.session_id,
            )
        if action == "message":
            return MessageService(service.db).publish(
                capability_class="first_class", run_id=str(lineage.run_id), author_lane_id=str(lineage.lane_id),
                task_id=lineage.task_id, kind=str(payload["kind"]), payload=dict(payload["payload"]),
                recipients=list(payload["recipients"]), references=list(payload.get("references", [])),
                blocking=bool(payload.get("blocking", False)), actor_session_id=lineage.session_id,
            )
        if action == "answer":
            return MessageService(service.db).answer(
                capability_class="first_class", run_id=str(lineage.run_id), author_lane_id=str(lineage.lane_id),
                question_id=str(payload["question_id"]), payload=dict(payload["payload"]),
                references=list(payload.get("references", [])), actor_session_id=lineage.session_id,
            )
        if action == "arrive":
            return RendezvousService(service.db).arrive(
                capability_class="first_class", run_id=str(lineage.run_id), lane_id=str(lineage.lane_id),
                task_id=lineage.task_id, rendezvous_id=str(payload["rendezvous_id"]), summary=str(payload["summary"]),
                context_version=int(payload.get("context_version", 1)),
                base_source_identity=str(payload.get("base_source_identity") or ""),
                final_source_identity=str(payload.get("final_source_identity") or ""),
                artifact=dict(payload.get("artifact") or {}), interfaces=dict(payload.get("interfaces") or {}),
                evidence=list(payload.get("evidence") or []), warnings=list(payload.get("warnings") or []),
                actor_session_id=lineage.session_id,
            )
        if action == "fork":
            lane_id = "lane-" + uuid.uuid4().hex[:12]
            tasks = [str(item) for item in payload["tasks"]]

            def operation(conn: Any, revision: int) -> dict[str, Any]:
                created = create_lane_in_transaction(
                    conn, revision, run_id=str(lineage.run_id), lane_id=lane_id,
                    parent_lane_id=str(lineage.lane_id), role=str(payload.get("role", "specialist")),
                    workspace_mode=str(payload.get("workspace_mode", "exclusive")),
                )
                queued = enqueue_tasks_in_transaction(conn, revision, lane_id=lane_id, task_ids=tasks)
                return {**created, **queued}

            result, revision, _ = service.mutate(
                actor=lineage.session_id, entity_type="workflow_lane", entity_id=lane_id,
                event_type="workflow.lane.forked", payload={"parent_lane_id": lineage.lane_id, "tasks": tasks}, operation=operation,
            )
            return {**result, "project_revision": revision}
        if action == "publish_interface":
            def operation(conn: Any, revision: int) -> dict[str, Any]:
                owner = conn.execute("SELECT owner_task_id,state FROM interfaces WHERE id=?", (payload["interface_id"],)).fetchone()
                if not owner or owner["owner_task_id"] != lineage.task_id:
                    raise TodoError("interface_owner_mismatch", "Only the owning task may publish an interface")
                fn = revise_interface if owner["state"] == "frozen" else freeze_interface
                result = fn(conn, service.paths.repo_root, str(payload["interface_id"]), str(payload["version"]), revision)
                if result["content_hash"] != payload["content_hash"]:
                    raise TodoError("interface_hash_mismatch", "Published interface hash differs from authoritative source")
                return result
            result, revision, _ = service.mutate(
                actor=lineage.session_id, entity_type="interface", entity_id=str(payload["interface_id"]),
                event_type="workflow.interface.published", payload={"version": payload["version"]}, operation=operation,
            )
            return {**result, "project_revision": revision}
        if action == "run_gates":
            with service.db.read() as conn:
                gates = required_gates(conn, lineage.task_id) if payload.get("required", True) else [dict(row) for row in conn.execute("SELECT * FROM gates WHERE task_id=?", (lineage.task_id,))]
            results = []
            for gate in gates:
                result, revision = run_gate(service.db, service.paths, service.project, str(gate["id"]), None, authorized_claim_id=lineage.claim_id)
                results.append({**result, "project_revision": revision})
            service.refresh({lineage.task_id})
            return {"status": "passed" if all(item.get("status") == "passed" for item in results) else "blocked", "gates": results}
        if action in {"accept_child", "reject_child"}:
            child_id = str(payload["child_execution_id"])
            target = "accepted" if action == "accept_child" else "rejected"
            def operation(conn: Any, revision: int) -> dict[str, Any]:
                result = disposition_child_execution_for_claim(
                    conn, str(lineage.claim_id), child_id, action="accept" if action == "accept_child" else "reject"
                )
                conn.execute(
                    "UPDATE workflow_child_result_candidates SET state=?,decided_at=?,decision_revision=? "
                    "WHERE child_execution_id=? AND parent_claim_id=? AND state='collected'",
                    (target, utc_now(), revision, child_id, lineage.claim_id),
                )
                return result
            result, revision, _ = service.mutate(
                actor=lineage.session_id, entity_type="child_execution", entity_id=child_id,
                event_type=f"workflow.child.{target}", payload={"child_execution_id": child_id}, operation=operation,
            )
            return {**result, "project_revision": revision, "parent_task_completed": False}
        if action == "request_integration":
            return {"status": "attention_required", "integration_request": dict(payload), "warnings": ["integration queue requires immutable published artifact ids"]}
        raise TodoError("invalid_coordination_action", "Coordination action is unsupported")

    def _child_scope(self, service: Service, claim_id: str, *, access: str) -> tuple[list[str], list[str]]:
        with service.db.read() as conn:
            claim = conn.execute("SELECT task_id FROM claims WHERE id=? AND state='active'", (claim_id,)).fetchone()
            if not claim:
                raise TodoError("invalid_claim_authority", "Parent claim is inactive")
            parents = scopes_for(conn, claim["task_id"], "exclusive" if access == "write" else None)
        for parent in parents:
            target = service.paths.repo_root / parent
            if target.is_dir():
                files = sorted(path for path in target.rglob("*") if path.is_file() and ".git" not in path.parts)
                if files:
                    return parents, [str(files[0].relative_to(service.paths.repo_root))]
        if len(parents) > 1:
            return parents, [parents[0]]
        raise TodoError("child_scope_not_strict", "No strict bounded child scope can be derived")

    def delegate_task(self, capability: AuthorizedCapability, *, objective: str, mode: str) -> Mapping[str, Any]:
        service = self._resolve_service(capability)
        lineage = capability.lineage
        require_role_action(str(lineage.role), "delegate_child")
        if self.local_worker_adapter is None:
            return {
                "status": "local_unavailable",
                "fallback_authorization": {
                    "specialized_skill": "local-coding-worker", "permitted_operation": "continue directly in Codex",
                    "reason": "local worker is unavailable", "scope": {"task_id": lineage.task_id}, "access": "read_only",
                },
            }
        access = "read" if mode == "readonly" else "write"
        try:
            parent_paths, child_paths = self._child_scope(service, str(lineage.claim_id), access=access)
        except TodoError as exc:
            return {
                "status": "not_eligible", "fallback_authorization": {
                    "specialized_skill": "local-coding-worker", "permitted_operation": "continue directly in Codex",
                    "reason": exc.code, "scope": {"task_id": lineage.task_id}, "access": "read_only",
                },
            }
        packet = compose_child_packet(
            delegated_objective=objective, parent_constraints=["remain subordinate to the parent claim"],
            parent_authorized_paths=parent_paths, child_authorized_paths=child_paths, source_packet_refs=[],
            required_output_schema={"kind": sorted(CHILD_RESULT_KINDS), "summary": "bounded"},
            candidate_gates=[], acceptance_gates=[],
        )
        capabilities = WorkflowCapabilityStore(service.db)
        parent = capability

        def operation(conn: Any, revision: int) -> dict[str, Any]:
            child = authorize_child_execution_for_claim(
                conn, service.paths.repo_root, str(lineage.claim_id), objective=objective,
                scopes=child_paths, gates=[], access=access,
            )
            child_lineage = CapabilityLineage(
                "child", lineage.project_uuid, lineage.repository_identity, lineage.session_id,
                lineage.claim_id, None, None, None, lineage.task_id, child_operations(), 1,
                parent_capability_id=parent.id, child_execution_id=str(child["child_execution_id"]),
            )
            handle, authorized = capabilities.stage_child(conn, lineage=child_lineage, parent=parent, revision=revision)
            return {
                "status": "delegated", "delegation_handle": handle,
                "child_execution_id": child["child_execution_id"], "capability_id": authorized.id,
                "packet_reference": content_hash(packet), "packet_size_bytes": len(json.dumps(packet).encode()),
            }
        result, revision, _ = service.mutate(
            actor=lineage.session_id, entity_type="child_execution", entity_id=lambda value: value["child_execution_id"],
            event_type="workflow.child.delegated", payload={"task_id": lineage.task_id}, operation=operation,
        )
        child_handle = str(result["delegation_handle"])
        self.locator.register(child_handle, service.paths.repo_root)
        adapter = self.local_worker_adapter.delegate(
            repo=service.paths.repo_root, parent_claim_ref=str(lineage.claim_id), objective_ref=content_hash(objective),
            packet_ref=str(result["packet_reference"]), mode=mode,
        )
        if adapter.get("status") in {"local_unavailable", "not_eligible"}:
            self.coordinate_task(capability, action="reject_child", payload={"child_execution_id": result["child_execution_id"], "reason": adapter.get("status")})
            WorkflowCapabilityStore(service.db).revoke(child_handle, actor_session_id=lineage.session_id)
            self.locator.forget(child_handle)
            return {
                "status": adapter["status"], "fallback_authorization": {
                    "specialized_skill": "local-coding-worker", "permitted_operation": "continue directly in Codex",
                    "reason": str(adapter["status"]), "scope": {"task_id": lineage.task_id, "paths": child_paths}, "access": "read_only",
                },
            }
        return {**result, "project_revision": revision, "worker_status": adapter.get("status", "running")}

    def collect_delegation(self, capability: AuthorizedCapability) -> Mapping[str, Any]:
        service = self._resolve_service(capability)
        child_id = str(capability.lineage.child_execution_id)
        adapter_result = self.local_worker_adapter.collect(repo=service.paths.repo_root, execution_id=child_id) if self.local_worker_adapter else {"status": "running"}
        with service.db.read() as conn:
            state = child_execution_status_for_claim(conn, str(capability.lineage.claim_id), child_id)
        if adapter_result.get("status") not in {"candidate_available", "succeeded", "ready_for_acceptance"}:
            return {"status": "running", "child": state}
        kind = str(adapter_result.get("kind", "source_finding"))
        if kind not in CHILD_RESULT_KINDS:
            raise TodoError("invalid_child_result_kind", "Local child returned an unsupported candidate kind")
        candidate_id = str(uuid.uuid5(uuid.UUID(child_id), content_hash(adapter_result)))

        def operation(conn: Any, revision: int) -> dict[str, Any]:
            candidate_payload = dict(adapter_result.get("result") or {})
            conn.execute(
                "UPDATE child_executions SET state='ready_for_acceptance',result_json=?,completed_at=? WHERE id=?",
                (json.dumps(candidate_payload, sort_keys=True), utc_now(), child_id),
            )
            conn.execute(
                "UPDATE child_attempts SET state='ready_for_acceptance',result_json=?,completed_at=? "
                "WHERE child_execution_id=? AND state='active'",
                (json.dumps(candidate_payload, sort_keys=True), utc_now(), child_id),
            )
            conn.execute(
                "INSERT OR IGNORE INTO workflow_child_result_candidates(id,child_execution_id,parent_claim_id,kind,payload_json,artifact_refs_json,state,created_at) "
                "VALUES(?,?,?,?,?,?,'collected',?)",
                (candidate_id, child_id, capability.lineage.claim_id, kind,
                 json.dumps(candidate_payload, sort_keys=True),
                 json.dumps(list(adapter_result.get("artifacts") or []), sort_keys=True), utc_now()),
            )
            return {"status": "candidate_available", "candidate_id": candidate_id, "kind": kind}
        result, revision, _ = service.mutate(
            actor=capability.lineage.session_id, entity_type="workflow_child_candidate", entity_id=candidate_id,
            event_type="workflow.child.collected", payload={"child_execution_id": child_id}, operation=operation,
        )
        return {**result, "project_revision": revision, "parent_task_completed": False}

    def finish_task(self, capability: AuthorizedCapability, *, action: str, disposition: str | None, note: str | None, reason: str | None) -> Mapping[str, Any]:
        service = self._resolve_service(capability)
        lineage = capability.lineage
        require_role_action(str(lineage.role), "finish_task")
        if action == "complete":
            # Required completion gates are lifecycle authority, not an explicit
            # validator-role operation. They always run for the parent claim.
            with service.db.read() as conn:
                completion_gates = required_gates(conn, lineage.task_id)
            for gate in completion_gates:
                run_gate(
                    service.db, service.paths, service.project, str(gate["id"]), None,
                    authorized_claim_id=lineage.claim_id,
                )
            capabilities = WorkflowCapabilityStore(service.db)
            rendezvous = RendezvousService(service.db)
            with service.db.read() as conn:
                dispatch = conn.execute(
                    "SELECT * FROM workflow_dispatches WHERE claim_id=? AND lane_id=? AND state='active'",
                    (lineage.claim_id, lineage.lane_id),
                ).fetchone()
            if not dispatch:
                raise TodoError("workflow_dispatch_inactive", "Completion requires the active first-class dispatch")

            def terminal(conn: Any, revision: int, claim: Any, task: Any, handoff: dict[str, Any]) -> dict[str, Any]:
                arrivals = []
                later = conn.execute(
                    "SELECT 1 FROM workflow_lane_tasks current JOIN workflow_lane_tasks pending "
                    "ON pending.lane_id=current.lane_id AND pending.position>current.position "
                    "WHERE current.lane_id=? AND current.task_id=? AND pending.state NOT IN ('completed','cancelled','skipped') LIMIT 1",
                    (lineage.lane_id, lineage.task_id),
                ).fetchone()
                if not later:
                    for row in conn.execute(
                        "SELECT r.id FROM workflow_rendezvous r JOIN workflow_rendezvous_participants p ON p.rendezvous_id=r.id "
                        "WHERE r.run_id=? AND p.lane_id=? AND r.state='open' ORDER BY r.id",
                        (lineage.run_id, lineage.lane_id),
                    ):
                        arrivals.append(rendezvous._arrive_in_transaction(
                            conn, revision, capability_class="first_class", run_id=str(lineage.run_id),
                            lane_id=str(lineage.lane_id), rendezvous_id=str(row["id"]), task_id=lineage.task_id,
                            summary=note or "task completed", base_source_identity=str(claim["baseline_head"] or "unknown"),
                            final_source_identity=str(handoff.get("git_head") or "unknown"),
                            artifact={"kind": "commit", "ref": str(handoff.get("git_head") or "unknown")},
                            interfaces={}, evidence=[{"type": "handoff", "id": handoff.get("task_id")}], warnings=[],
                            context_version=int(dispatch["context_version"]),
                        ))
                advanced = advance_lane_in_transaction(
                    conn, revision, lane_id=str(lineage.lane_id), task_id=lineage.task_id, dispatch_id=str(dispatch["id"])
                )
                capabilities.stage_revoke(conn, capability_id=capability.id, family=True)
                return {"lane": advanced, "rendezvous_arrivals": arrivals, "terminal": True}

            completed = service.complete_claim_id(
                str(lineage.claim_id), disposition or "implemented", note or "", terminal_hook=terminal
            )
            return {**completed, "status": "idle", "terminal": True}

        status = {"handoff": "in_progress", "block": "blocked", "release": "in_progress"}[action]
        def operation(conn: Any, revision: int) -> dict[str, Any]:
            claim = conn.execute("SELECT * FROM claims WHERE id=? AND state='active'", (lineage.claim_id,)).fetchone()
            if not claim:
                raise TodoError("invalid_claim_authority", "Workflow claim is inactive")
            handoff_id = None
            if action in {"handoff", "block"}:
                handoff_id = str(uuid.uuid4())
                body = service._handoff_payload(conn, claim, note or "")
                conn.execute(
                    "INSERT INTO handoffs(id,task_id,claim_id,kind,note,payload_json,created_at,revision) VALUES(?,?,?,?,?,?,?,?)",
                    (handoff_id, lineage.task_id, lineage.claim_id, action, note or "", json.dumps(body, sort_keys=True), utc_now(), revision),
                )
            release_claim_id(conn, str(lineage.claim_id), next_status=status, reason=reason)
            conn.execute("UPDATE workflow_dispatches SET state='released',released_at=?,revision=? WHERE id=?", (utc_now(), revision, conn.execute("SELECT id FROM workflow_dispatches WHERE claim_id=? AND state='active'", (lineage.claim_id,)).fetchone()[0]))
            WorkflowCapabilityStore(service.db).stage_revoke(conn, capability_id=capability.id, family=True)
            return {"status": "finished", "task_id": lineage.task_id, "handoff_id": handoff_id, "terminal": True}
        result, revision, projection = service.mutate(
            actor=lineage.session_id, entity_type="task", entity_id=lineage.task_id,
            event_type=f"workflow.task.{action}", payload={"reason": reason}, operation=operation,
        )
        return {**result, "project_revision": revision, "projection": projection}
