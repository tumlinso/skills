"""Supported additive facade over todo-orchestrator's private sidecars."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from ..background.host import HostCoordinator
from ..background.store import BackgroundStore
from .contracts import (
    ContractError,
    normalize_artifact_ref,
    normalize_command_spec,
    normalize_evidence_summary,
    normalize_resource_request,
    normalize_source_identity,
)
from .source import capture_source_identity


def _private_resource_request(value: object | None) -> dict[str, Any]:
    normalized = normalize_resource_request(value)
    return {key: item for key, item in normalized.items() if key != "schema_version"}


class JobFacade:
    def __init__(self, store: BackgroundStore):
        self._store = store

    def enqueue(
        self,
        *,
        kind: str,
        command: object,
        source_identity: object,
        resource_request: object | None = None,
        dependencies: Iterable[str] = (),
        priority: int = 40,
        retry_limit: int = 0,
        dedup_key: str | None = None,
        watch_id: str | None = None,
        task_id: str | None = None,
        todo_revision: int | None = None,
    ) -> dict[str, object]:
        if not isinstance(kind, str) or not kind:
            raise ContractError("job kind must be a non-empty string")
        if isinstance(priority, bool) or not isinstance(priority, int):
            raise ContractError("job priority must be an integer")
        if isinstance(retry_limit, bool) or not isinstance(retry_limit, int) or retry_limit < 0:
            raise ContractError("job retry_limit must be a non-negative integer")
        spec = normalize_command_spec(command)
        source = normalize_source_identity(source_identity)
        job: dict[str, object] = {
            "kind": kind,
            "argv": spec["argv"],
            "cwd": spec["cwd"],
            "env": spec["env"],
            "timeout": spec["timeout_seconds"],
            "resources": _private_resource_request(resource_request),
            "source_fingerprint": source["fingerprint"],
            "snapshot": source,
            "priority": priority,
            "retry_limit": retry_limit,
            "task_id": task_id,
            "todo_revision": todo_revision,
        }
        if dedup_key is not None:
            job["dedup_key"] = dedup_key
        if watch_id is not None:
            job["watch_id"] = watch_id
        job_id, created = self._store.enqueue(job, dependencies)
        return {"job_id": job_id, "created": created}

    def result(self, identifier: str) -> dict[str, object] | None:
        raw = self._store.result(identifier)
        if raw is None:
            return None
        stored = raw.get("summary")
        if isinstance(stored, dict) and stored.get("schema_version") == 1:
            value = dict(stored)
        else:
            value = {
                "schema_version": 1,
                "status": str(raw["status"]),
                "valid": bool(raw["valid"]),
                "contaminated": bool(raw["contaminated"]),
                "severity": int(raw["severity"]),
                "summary": stored if isinstance(stored, dict) else {"value": stored},
                "artifacts": [],
            }
        value.update({
            "job_id": str(raw["job_id"]),
            "result_id": str(raw["id"]),
            "status": str(raw["status"]),
            "valid": bool(raw["valid"]),
            "contaminated": bool(raw["contaminated"]),
            "severity": int(raw["severity"]),
            "classification": raw.get("classification"),
            "parser_version": raw.get("parser_version"),
            "source_identity": raw.get("snapshot", {}),
            "artifacts": [
                normalize_artifact_ref({
                    "schema_version": 1,
                    "artifact_id": item["id"],
                    "job_id": item["job_id"],
                    "kind": item["kind"],
                    "path": item["path"],
                    "content_hash": item["content_hash"],
                    "complete": bool(item["complete"]),
                })
                for item in raw.get("artifacts", [])
            ],
        })
        return normalize_evidence_summary(value)

    def record_external(
        self,
        *,
        kind: str,
        command: object,
        source_identity: object,
        evidence: object,
    ) -> dict[str, str]:
        spec = normalize_command_spec(command)
        source = normalize_source_identity(source_identity)
        summary = normalize_evidence_summary(evidence)
        artifacts = summary.pop("artifacts")
        summary.pop("source_identity", None)
        summary.pop("job_id", None)
        summary.pop("result_id", None)
        job_id, result_id = self._store.record_external_result(
            kind=kind,
            argv=spec["argv"],
            cwd=spec["cwd"],
            source_fingerprint=source["fingerprint"],
            snapshot=source,
            result=summary,
            artifacts=[{key: item.get(key) for key in ("kind", "path", "content_hash", "complete")} for item in artifacts],
        )
        return {"job_id": job_id, "result_id": result_id}


class ArtifactFacade:
    def __init__(self, store: BackgroundStore):
        self._store = store

    def record(self, *, job_id: str, artifact: object, attempt_id: str | None = None) -> str:
        value = normalize_artifact_ref(artifact)
        return self._store.record_artifact(
            job_id,
            attempt_id,
            str(value["kind"]),
            str(value["path"]),
            value.get("content_hash"),
            bool(value["complete"]),
        )


class SnapshotFacade:
    @staticmethod
    def capture(repo_root: str | Path) -> dict[str, object]:
        return capture_source_identity(repo_root)


class HostResourceFacade:
    def __init__(self, coordinator: HostCoordinator):
        self._coordinator = coordinator

    def upsert(self, resources: list[dict[str, object]]) -> None:
        normalized = []
        for item in resources:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                raise ContractError("host resources require a non-empty id")
            kind = item.get("kind", "accelerator")
            tags = item.get("tags", {})
            if not isinstance(kind, str) or not kind or not isinstance(tags, dict):
                raise ContractError("host resource kind and tags are invalid")
            normalized.append({"id": item["id"], "kind": kind, "tags": tags, "enabled": bool(item.get("enabled", True))})
        self._coordinator.upsert_resources(normalized)

    def list(self, *, kind: str | None = None) -> list[dict[str, object]]:
        try:
            connection = self._coordinator.connect(readonly=True)
        except sqlite3.Error:
            return []
        try:
            if kind is None:
                rows = connection.execute("SELECT * FROM host_resources ORDER BY id").fetchall()
            else:
                rows = connection.execute("SELECT * FROM host_resources WHERE kind=? ORDER BY id", (kind,)).fetchall()
            return [
                {"id": str(row["id"]), "kind": str(row["kind"]), "tags": json.loads(row["tags_json"]), "enabled": bool(row["enabled"])}
                for row in rows
            ]
        finally:
            connection.close()

    def reserve_background(self, *, project_root: str | Path, job_id: str, attempt_id: str,
                           resource_request: object, pid: int | None = None) -> dict[str, object] | None:
        reserved = self._coordinator.reserve_background(
            project_root=project_root,
            job_id=job_id,
            attempt_id=attempt_id,
            request=_private_resource_request(resource_request),
            pid=pid or os.getpid(),
        )
        return None if reserved is None else {"owner_id": reserved[0], "resource_ids": reserved[1]}

    def begin_foreground(self, *, project_root: str | Path, resource_request: object,
                         pid: int | None = None) -> dict[str, object]:
        owner_id, resources = self._coordinator.begin_foreground(
            project_root=project_root,
            request=_private_resource_request(resource_request),
            pid=pid or os.getpid(),
        )
        return {"owner_id": owner_id, "resource_ids": resources}

    def activate_foreground(self, reservation: dict[str, object]) -> bool:
        return self._coordinator.activate_foreground(str(reservation["owner_id"]), [str(item) for item in reservation["resource_ids"]])

    def preempt_requested(self, owner_id: str) -> bool:
        return self._coordinator.preempt_requested(owner_id)

    def heartbeat(self, owner_id: str, *, pid: int | None = None) -> None:
        self._coordinator.heartbeat(owner_id, pid)

    def release(self, owner_id: str) -> None:
        self._coordinator.release(owner_id)


class RuntimeFacade:
    """One supported namespace; each component remains independently usable."""

    def __init__(self, project_root: str | Path, *, store: BackgroundStore | None = None,
                 host: HostCoordinator | None = None):
        private_store = store or BackgroundStore(project_root)
        self.jobs = JobFacade(private_store)
        self.artifacts = ArtifactFacade(private_store)
        self.snapshots = SnapshotFacade()
        self.host = HostResourceFacade(host or HostCoordinator())
