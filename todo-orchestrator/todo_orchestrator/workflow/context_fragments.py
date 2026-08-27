"""Versioned, bounded workflow context fragments.

The fragment store is deliberately a client of the existing todo database.  It
does not own a connection or revision counter: every write is performed through
``Database.mutate`` and is therefore revisioned with the rest of todo state.

First-class worker capsules and local-child packets are separate compositions.
In particular, child packets are built from an explicit allowlist and never by
filtering a first-class capsule after the fact.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from ..config import utc_now
from ..models import TodoError
from .foundation import (
    CHILD_PACKET_BUDGET_BYTES,
    COORDINATE_TASK_BUDGET_BYTES,
    NEXT_TASK_BUDGET_BYTES,
    PROTOCOL_VERSION,
    WorkflowDatabase,
    canonical_json,
    content_hash,
    require_bounded_payload,
    require_child_scope_subset,
)


FRAGMENT_KINDS = frozenset({
    "run_charter",
    "lane_brief",
    "task_brief",
    "decision_ledger",
    "delta_inbox",
    "source_packet_ref",
})

# These names identify values that must remain behind the workflow boundary.
# Packet *references* are allowed; packet bodies and process output are not.
_SECRET_KEYS = frozenset({
    "token",
    "claim_token",
    "session_token",
    "child_token",
    "worker_token",
    "recovery_token",
    "approval_token",
    "api_key",
    "password",
    "secret",
    "gpu_identifier",
    "model_endpoint",
    "packet_body",
    "raw_packet",
    "log",
    "logs",
    "transcript",
    "transcripts",
    "stdout",
    "stderr",
})

_SOURCE_REFERENCE_KEYS = frozenset({
    "packet_id",
    "content_hash",
    "target",
    "symbols",
    "paths",
    "budget_bytes",
    "compiler",
    "created_revision",
})

_CHILD_PACKET_KEYS = frozenset({
    "protocol_version",
    "packet_class",
    "delegated_objective",
    "parent_constraints",
    "authorized_paths",
    "source_packet_refs",
    "required_output_schema",
    "candidate_gates",
    "acceptance_gates",
    "interface_facts",
})


def _reject_secrets(value: object, *, path: str = "context") -> None:
    if isinstance(value, Mapping):
        for raw_key, item in value.items():
            key = str(raw_key).lower()
            if key in _SECRET_KEYS or key.endswith("_token") or key.endswith("_secret"):
                raise TodoError(
                    "workflow_secret_forbidden",
                    f"Secret or unbounded diagnostic field is forbidden at {path}.{raw_key}",
                )
            _reject_secrets(item, path=f"{path}.{raw_key}")
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_secrets(item, path=f"{path}[{index}]")


def _validate_source_references(references: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(references, (str, bytes, Mapping)):
        raise TodoError("invalid_source_packet_reference", "Source packet references must be a list")
    normalized: list[dict[str, Any]] = []
    for reference in references:
        if not isinstance(reference, Mapping):
            raise TodoError("invalid_source_packet_reference", "Each source packet reference must be an object")
        extra = set(reference) - _SOURCE_REFERENCE_KEYS
        if extra:
            raise TodoError(
                "source_packet_reference_only",
                "Source context must use bounded packet references, not source or packet bodies",
                details={"forbidden_fields": sorted(extra)},
            )
        if not reference.get("packet_id") or not reference.get("content_hash"):
            raise TodoError("invalid_source_packet_reference", "packet_id and content_hash are required")
        paths = reference.get("paths", [])
        if isinstance(paths, (str, bytes, Mapping)) or not isinstance(paths, Sequence):
            raise TodoError("invalid_source_packet_reference", "Source packet paths must be a repository-relative list")
        if not paths:
            raise TodoError("source_packet_scope_required", "Source packet references require explicit bounded paths")
        _minimal_scopes([str(path) for path in paths])
        normalized.append(dict(reference))
    _reject_secrets(normalized, path="source_packet_refs")
    return normalized


def _minimal_scopes(paths: Sequence[str]) -> list[str]:
    normalized: list[PurePosixPath] = []
    for raw in paths:
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise TodoError("invalid_child_scope", f"Invalid repository-relative scope: {raw}")
        if any(path == existing or existing in path.parents for existing in normalized):
            continue
        normalized = [existing for existing in normalized if path not in existing.parents]
        normalized.append(path)
    return sorted(str(path) for path in normalized)


def _validate_owner_binding(conn: Any, owner: "FragmentOwner") -> None:
    if not conn.execute("SELECT 1 FROM workflow_runs WHERE id=?", (owner.run_id,)).fetchone():
        raise TodoError("fragment_run_not_found", "Fragment run is not authoritative")
    if owner.lane_id and not conn.execute(
        "SELECT 1 FROM workflow_lanes WHERE id=? AND run_id=?", (owner.lane_id, owner.run_id)
    ).fetchone():
        raise TodoError("fragment_lane_run_mismatch", "Fragment lane does not belong to its run")
    if owner.task_id:
        if owner.lane_id:
            found = conn.execute(
                "SELECT 1 FROM workflow_lane_tasks WHERE lane_id=? AND task_id=?",
                (owner.lane_id, owner.task_id),
            ).fetchone()
        else:
            found = conn.execute(
                "SELECT 1 FROM workflow_lane_tasks lt JOIN workflow_lanes l ON l.id=lt.lane_id "
                "WHERE l.run_id=? AND lt.task_id=?",
                (owner.run_id, owner.task_id),
            ).fetchone()
        if not found:
            raise TodoError("fragment_task_owner_mismatch", "Fragment task is not assigned within its owner scope")


@dataclass(frozen=True)
class FragmentOwner:
    run_id: str
    lane_id: str | None = None
    task_id: str | None = None

    def validate(self, kind: str) -> None:
        if not self.run_id:
            raise TodoError("invalid_fragment_owner", "run_id is required")
        if kind == "run_charter" and (self.lane_id is not None or self.task_id is not None):
            raise TodoError("invalid_fragment_owner", "run charter must be owned by the run")
        if kind in {"lane_brief", "delta_inbox"} and not self.lane_id:
            raise TodoError("invalid_fragment_owner", f"{kind} requires a lane owner")
        if kind == "task_brief" and not self.task_id:
            raise TodoError("invalid_fragment_owner", "task brief requires a task owner")

    def as_json(self) -> dict[str, str]:
        result = {"run_id": self.run_id}
        if self.lane_id is not None:
            result["lane_id"] = self.lane_id
        if self.task_id is not None:
            result["task_id"] = self.task_id
        return result


@dataclass(frozen=True)
class ContextFragment:
    id: str
    owner: FragmentOwner
    kind: str
    version: int
    content: dict[str, Any]
    content_hash: str
    creation_revision: int
    invalidated_at: str | None
    invalidation_revision: int | None
    superseded_by: str | None

    @property
    def active(self) -> bool:
        return self.invalidated_at is None and self.superseded_by is None

    def reference(self) -> dict[str, Any]:
        return {
            "fragment_id": self.id,
            "kind": self.kind,
            "owner_scope": self.owner.as_json(),
            "version": self.version,
            "content_hash": self.content_hash,
            "creation_revision": self.creation_revision,
            "invalidated": not self.active,
        }


def _fragment_from_row(row: Any) -> ContextFragment:
    return ContextFragment(
        id=str(row["id"]),
        owner=FragmentOwner(
            run_id=str(row["run_id"]),
            lane_id=row["lane_id"],
            task_id=row["task_id"],
        ),
        kind=str(row["kind"]),
        version=int(row["version"]),
        content=json.loads(row["content_json"]),
        content_hash=str(row["content_hash"]),
        creation_revision=int(row["creation_revision"]),
        invalidated_at=row["invalidated_at"],
        invalidation_revision=row["invalidation_revision"],
        superseded_by=row["superseded_by"],
    )


def _owner_sql(owner: FragmentOwner) -> tuple[str, list[object]]:
    return (
        "run_id=? AND lane_id IS ? AND task_id IS ?",
        [owner.run_id, owner.lane_id, owner.task_id],
    )


class ContextFragmentStore:
    """Transactional store and bounded composer for workflow context."""

    def __init__(self, db: WorkflowDatabase):
        self.db = db

    def publish(
        self,
        *,
        actor_session_id: str | None,
        owner: FragmentOwner,
        kind: str,
        content: Mapping[str, Any],
        invalidate_fragment_ids: Sequence[str] = (),
    ) -> tuple[ContextFragment, int]:
        if kind not in FRAGMENT_KINDS:
            raise TodoError("invalid_fragment_kind", f"Unknown context fragment kind: {kind}")
        owner.validate(kind)
        normalized = dict(content)
        _reject_secrets(normalized)
        if kind == "source_packet_ref":
            normalized = {"references": _validate_source_references(normalized.get("references", []))}
        digest = content_hash(normalized)
        fragment_id = str(uuid.uuid4())
        invalidations = tuple(dict.fromkeys(invalidate_fragment_ids))

        def operation(conn: Any, revision: int) -> ContextFragment:
            _validate_owner_binding(conn, owner)
            clause, args = _owner_sql(owner)
            existing = conn.execute(
                f"SELECT * FROM workflow_context_fragments WHERE {clause} AND kind=? AND content_hash=?",
                [*args, kind, digest],
            ).fetchone()
            if existing is not None:
                return _fragment_from_row(existing)

            prior = conn.execute(
                f"SELECT * FROM workflow_context_fragments WHERE {clause} AND kind=? "
                "ORDER BY version DESC LIMIT 1",
                [*args, kind],
            ).fetchone()
            version = int(prior["version"]) + 1 if prior is not None else 1
            now = utc_now()
            conn.execute(
                "INSERT INTO workflow_context_fragments("
                "id,run_id,lane_id,task_id,kind,owner_scope_json,version,content_json,content_hash,"
                "creation_revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    fragment_id,
                    owner.run_id,
                    owner.lane_id,
                    owner.task_id,
                    kind,
                    canonical_json(owner.as_json()),
                    version,
                    canonical_json(normalized),
                    digest,
                    revision,
                    now,
                ),
            )
            if prior is not None and prior["invalidated_at"] is None:
                conn.execute(
                    "UPDATE workflow_context_fragments SET invalidated_at=?,invalidation_revision=?,superseded_by=? "
                    "WHERE id=?",
                    (now, revision, fragment_id, prior["id"]),
                )
            for target_id in invalidations:
                target = conn.execute(
                    "SELECT run_id FROM workflow_context_fragments WHERE id=?", (target_id,)
                ).fetchone()
                if target is None or target["run_id"] != owner.run_id:
                    raise TodoError(
                        "invalid_fragment_invalidation",
                        "Only an existing fragment in the same run may be invalidated",
                    )
                conn.execute(
                    "UPDATE workflow_context_fragments SET invalidated_at=COALESCE(invalidated_at,?),"
                    "invalidation_revision=COALESCE(invalidation_revision,?) WHERE id=?",
                    (now, revision, target_id),
                )
            row = conn.execute("SELECT * FROM workflow_context_fragments WHERE id=?", (fragment_id,)).fetchone()
            return _fragment_from_row(row)

        return self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_context_fragment",
            entity_id=lambda fragment: fragment.id,
            event_type="workflow_context_fragment_published",
            payload=lambda fragment: {
                "kind": fragment.kind,
                "version": fragment.version,
                "content_hash": fragment.content_hash,
                "invalidated_fragment_ids": list(invalidations),
            },
            operation=operation,
        )

    def invalidate(
        self,
        *,
        actor_session_id: str | None,
        run_id: str,
        fragment_ids: Sequence[str],
        reason: str,
    ) -> tuple[list[dict[str, Any]], int]:
        targets = tuple(dict.fromkeys(fragment_ids))
        if not targets or not reason.strip():
            raise TodoError("invalid_fragment_invalidation", "Targets and a bounded reason are required")
        require_bounded_payload({"reason": reason}, limit=1024)

        def operation(conn: Any, revision: int) -> list[dict[str, Any]]:
            now = utc_now()
            changed: list[dict[str, Any]] = []
            for fragment_id in targets:
                row = conn.execute(
                    "SELECT * FROM workflow_context_fragments WHERE id=? AND run_id=?",
                    (fragment_id, run_id),
                ).fetchone()
                if row is None:
                    raise TodoError("fragment_not_found", f"Unknown fragment: {fragment_id}")
                if row["invalidated_at"] is None:
                    conn.execute(
                        "UPDATE workflow_context_fragments SET invalidated_at=?,invalidation_revision=? WHERE id=?",
                        (now, revision, fragment_id),
                    )
                    row = conn.execute(
                        "SELECT * FROM workflow_context_fragments WHERE id=?", (fragment_id,)
                    ).fetchone()
                changed.append(_fragment_from_row(row).reference())
            return changed

        return self.db.mutate(
            actor_session_id=actor_session_id,
            entity_type="workflow_context_fragment",
            entity_id=run_id,
            event_type="workflow_context_fragments_invalidated",
            payload={"fragment_ids": list(targets), "reason": reason},
            operation=operation,
        )

    def get(self, fragment_id: str) -> ContextFragment:
        with self.db.read() as conn:
            row = conn.execute(
                "SELECT * FROM workflow_context_fragments WHERE id=?", (fragment_id,)
            ).fetchone()
        if row is None:
            raise TodoError("fragment_not_found", f"Unknown fragment: {fragment_id}")
        return _fragment_from_row(row)

    def expand(self, fragment_id: str, *, budget_bytes: int) -> dict[str, Any]:
        if budget_bytes < 256 or budget_bytes > 64 * 1024:
            raise TodoError("invalid_context_budget", "Explicit inspection budget must be 256..65536 bytes")
        fragment = self.get(fragment_id)
        result = {"fragment": fragment.reference(), "content": fragment.content}
        require_bounded_payload(result, limit=budget_bytes, code="context_expansion_too_large")
        return result

    def active_for(self, *, run_id: str, lane_id: str, task_id: str) -> list[ContextFragment]:
        with self.db.read() as conn:
            rows = conn.execute(
                "SELECT * FROM workflow_context_fragments WHERE run_id=? AND invalidated_at IS NULL "
                "AND superseded_by IS NULL AND (lane_id IS NULL OR lane_id=?) "
                "AND (task_id IS NULL OR task_id=?) ORDER BY kind,version",
                (run_id, lane_id, task_id),
            ).fetchall()
        return [_fragment_from_row(row) for row in rows]

    def compose_first_class(
        self,
        *,
        run_id: str,
        lane_id: str,
        task_id: str,
        known_manifest: Mapping[str, object] | None = None,
        budget_bytes: int = NEXT_TASK_BUDGET_BYTES,
    ) -> dict[str, Any]:
        if budget_bytes > COORDINATE_TASK_BUDGET_BYTES or budget_bytes < 1024:
            raise TodoError("invalid_context_budget", "Normal workflow context budget must be 1024..8192 bytes")
        if known_manifest is not None and len(known_manifest) > 256:
            raise TodoError("context_manifest_too_large", "Known fragment manifest is limited to 256 entries")
        fragments = self.active_for(run_id=run_id, lane_id=lane_id, task_id=task_id)
        by_kind: dict[str, list[ContextFragment]] = {}
        for fragment in fragments:
            by_kind.setdefault(fragment.kind, []).append(fragment)
        manifest = [fragment.reference() for fragment in fragments]
        known = known_manifest or {}
        changed = [] if known_manifest is None else [
            reference
            for reference in manifest
            if not _known_reference_matches(known.get(reference["fragment_id"]), reference)
        ]
        active_ids = {str(reference["fragment_id"]) for reference in manifest}
        missing_known_ids = [str(fragment_id) for fragment_id in known if str(fragment_id) not in active_ids]
        if missing_known_ids:
            placeholders = ",".join("?" for _ in missing_known_ids)
            with self.db.read() as conn:
                rows = conn.execute(
                    f"SELECT * FROM workflow_context_fragments WHERE run_id=? AND id IN ({placeholders})",
                    [run_id, *missing_known_ids],
                ).fetchall()
            changed.extend(_fragment_from_row(row).reference() for row in rows)
        changed.sort(key=lambda item: (str(item["kind"]), int(item["version"]), str(item["fragment_id"])))

        def latest(kind: str) -> ContextFragment | None:
            candidates = by_kind.get(kind, [])
            return max(candidates, key=lambda item: item.version) if candidates else None

        charter = latest("run_charter")
        lane = latest("lane_brief")
        task = latest("task_brief")
        delta = latest("delta_inbox")
        result: dict[str, Any] = {
            "protocol_version": PROTOCOL_VERSION,
            "status": "context_stale" if known_manifest is not None and changed else "current",
            "run_id": run_id,
            "lane_id": lane_id,
            "task_id": task_id,
            "run_summary": _compact_content(charter, ("objective", "boundaries", "invariants", "acceptance_conditions", "glossary")),
            "lane_brief": _compact_content(lane, ("role", "authority", "ordered_tasks", "interfaces", "rendezvous", "workspace_mode")),
            "task_brief": _compact_content(task, ("objective", "next_action", "scope", "completion_contract", "tests", "gates", "forbidden_mutations")),
            "unread_delta": _compact_content(delta, ("cursor", "messages", "state_changes", "fragment_changes", "interface_invalidations", "rendezvous_changes")),
            "fragment_manifest": manifest,
            "changed_fragments": changed,
        }
        try:
            require_bounded_payload(result, limit=budget_bytes, code="context_capsule_too_large")
        except TodoError:
            # Delta bodies are non-critical expansion content. Safety-bearing run,
            # lane, and task constraints remain present or the capsule fails.
            if delta is not None:
                result["unread_delta"] = {"fragment_id": delta.id, "version": delta.version, "expand": True}
            require_bounded_payload(result, limit=budget_bytes, code="context_capsule_too_large")
        return result


def _compact_content(fragment: ContextFragment | None, keys: Iterable[str]) -> dict[str, Any]:
    if fragment is None:
        return {}
    result = {key: fragment.content[key] for key in keys if key in fragment.content}
    result["fragment_id"] = fragment.id
    result["version"] = fragment.version
    return result


def _known_reference_matches(known: object, reference: Mapping[str, Any]) -> bool:
    if isinstance(known, Mapping):
        known_version = known.get("version")
        known_hash = known.get("content_hash")
        return (
            (known_version is None or str(known_version) == str(reference["version"]))
            and (known_hash is None or str(known_hash) == str(reference["content_hash"]))
            and (known_version is not None or known_hash is not None)
        )
    return str(known) in {str(reference["version"]), str(reference["content_hash"])}


def compose_legacy_capsule(
    legacy: Mapping[str, Any], *, budget_bytes: int = NEXT_TASK_BUDGET_BYTES
) -> dict[str, Any]:
    """Normalize a v2 single-task capsule without inventing run semantics."""

    _reject_secrets(legacy)
    result = {
        "protocol_version": PROTOCOL_VERSION,
        "status": "current",
        "compatibility_mode": "legacy_v2_single_lane",
        "task": legacy.get("task", {}),
        "scope": legacy.get("scope", {}),
        "gates": legacy.get("gates", []),
        "checkpoints": legacy.get("checkpoints", []),
        "warnings": legacy.get("warnings", []),
    }
    require_bounded_payload(result, limit=budget_bytes, code="context_capsule_too_large")
    return result


def compose_child_packet(
    *,
    delegated_objective: str,
    parent_constraints: Sequence[str],
    parent_authorized_paths: Sequence[str],
    child_authorized_paths: Sequence[str],
    source_packet_refs: Sequence[Mapping[str, Any]],
    required_output_schema: Mapping[str, Any],
    candidate_gates: Sequence[str],
    acceptance_gates: Sequence[str],
    interface_facts: Sequence[Mapping[str, Any]] = (),
    budget_bytes: int = CHILD_PACKET_BUDGET_BYTES,
) -> dict[str, Any]:
    """Build a deliberately impoverished packet for one subordinate child."""

    if budget_bytes < 512 or budget_bytes > CHILD_PACKET_BUDGET_BYTES:
        raise TodoError("invalid_child_packet_budget", "Child packet budget must be 512..4096 bytes")
    if not delegated_objective.strip():
        raise TodoError("invalid_child_packet", "A bounded delegated objective is required")
    parent_paths = list(parent_authorized_paths)
    child_paths = list(child_authorized_paths)
    if not child_paths:
        raise TodoError("invalid_child_packet", "At least one authorized child path is required")
    require_child_scope_subset(parent_paths, child_paths)
    parent_minimal = _minimal_scopes(parent_paths)
    child_minimal = _minimal_scopes(child_paths)
    if parent_minimal == child_minimal:
        raise TodoError("child_scope_not_strict", "Child paths must be narrower than parent-authorized paths")
    references = _validate_source_references(source_packet_refs)
    for reference in references:
        source_paths = reference.get("paths", [])
        if source_paths:
            require_child_scope_subset(child_minimal, list(source_paths))
    packet = {
        "protocol_version": PROTOCOL_VERSION,
        "packet_class": "subordinate_local_child",
        "delegated_objective": delegated_objective,
        "parent_constraints": list(parent_constraints),
        "authorized_paths": child_minimal,
        "source_packet_refs": references,
        "required_output_schema": dict(required_output_schema),
        "candidate_gates": list(candidate_gates),
        "acceptance_gates": list(acceptance_gates),
        "interface_facts": [dict(item) for item in interface_facts],
    }
    if set(packet) != _CHILD_PACKET_KEYS:  # Defensive: additions require an explicit contract review.
        raise TodoError("invalid_child_packet", "Child packet fields differ from the frozen allowlist")
    _reject_secrets(packet, path="child_packet")
    require_bounded_payload(packet, limit=budget_bytes, code="child_packet_too_large")
    return packet
