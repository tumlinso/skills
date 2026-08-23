"""Lazy host-global authority for physical resources shared by project sidecars."""

from __future__ import annotations

import itertools
import json
import os
import sqlite3
import tempfile
import time
import uuid
from pathlib import Path

from .models import canonical_json, digest
from .resources import cpu_capacity, memory_capacity_bytes
from .store import _alive, _process_start


def _normalize_priority_class(value: str) -> str:
    # Lazy import avoids a cycle through runtime.__init__ -> facade -> host.
    from ..runtime.resources import normalize_priority_class
    return normalize_priority_class(value)


def _priority_value(value: str) -> int:
    from ..runtime.resources import priority_value
    return priority_value(value)


SCHEMA = """
CREATE TABLE IF NOT EXISTS host_resources(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, tags_json TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS host_owners(
 id TEXT PRIMARY KEY, owner_kind TEXT NOT NULL, project_root TEXT,
 job_id TEXT, attempt_id TEXT, service_id TEXT, pid INTEGER, process_start TEXT,
 state TEXT NOT NULL, preempt_requested INTEGER NOT NULL DEFAULT 0,
 priority_class TEXT NOT NULL DEFAULT 'background_cuda',
 preemptible INTEGER NOT NULL DEFAULT 1,
 cpu_threads INTEGER NOT NULL DEFAULT 0, ram_bytes INTEGER NOT NULL DEFAULT 0,
 acquired_at REAL NOT NULL, heartbeat_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS host_reservations(
 resource_id TEXT NOT NULL, owner_id TEXT NOT NULL, state TEXT NOT NULL,
 acquired_at REAL NOT NULL, heartbeat_at REAL NOT NULL,
 PRIMARY KEY(resource_id,owner_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_host_resource_exclusive
 ON host_reservations(resource_id) WHERE state='active';
CREATE TABLE IF NOT EXISTS host_foreground_intents(
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, resources_json TEXT NOT NULL,
 cpu_threads INTEGER NOT NULL DEFAULT 0, ram_bytes INTEGER NOT NULL DEFAULT 0,
 state TEXT NOT NULL, created_at REAL NOT NULL, heartbeat_at REAL NOT NULL
);
"""


def host_runtime_root() -> Path:
    override = os.environ.get("TODO_BACKGROUND_HOST_RUNTIME_DIR")
    if override:
        return Path(override).resolve()
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        candidate = Path(runtime)
        try:
            if candidate.is_dir() and candidate.stat().st_uid == os.getuid():
                return candidate / "codex-todo-orchestrator"
        except OSError:
            pass
    return Path(tempfile.gettempdir()) / f"codex-todo-orchestrator-{os.getuid()}"


def background_owner_id(project_root: str | Path, job_id: str, attempt_id: str) -> str:
    project = digest(str(Path(project_root).resolve()))[:16]
    return f"background:{project}:{job_id}:{attempt_id}"


class HostCoordinator:
    def __init__(self, *, create: bool = True, busy_timeout_ms: int = 2500):
        self.root = host_runtime_root()
        self.database = self.root / "physical-resources.sqlite3"
        self.busy_timeout_ms = busy_timeout_ms
        if create:
            self.initialize()

    def connect(self, *, readonly: bool = False) -> sqlite3.Connection:
        if readonly:
            connection = sqlite3.connect(f"file:{self.database}?mode=ro", uri=True, timeout=self.busy_timeout_ms / 1000)
        else:
            self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                self.root.chmod(0o700)
            except OSError:
                pass
            connection = sqlite3.connect(self.database, timeout=self.busy_timeout_ms / 1000, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        if not readonly:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
        return connection

    def initialize(self) -> None:
        connection = self.connect()
        try:
            connection.executescript(SCHEMA)
            columns = {str(row[1]) for row in connection.execute("PRAGMA table_info(host_owners)")}
            if "service_id" not in columns:
                connection.execute("ALTER TABLE host_owners ADD COLUMN service_id TEXT")
            if "priority_class" not in columns:
                connection.execute("ALTER TABLE host_owners ADD COLUMN priority_class TEXT NOT NULL DEFAULT 'background_cuda'")
            if "preemptible" not in columns:
                connection.execute("ALTER TABLE host_owners ADD COLUMN preemptible INTEGER NOT NULL DEFAULT 1")
        finally:
            connection.close()

    def _tx(self) -> sqlite3.Connection:
        connection = self.connect()
        connection.execute("BEGIN IMMEDIATE")
        return connection

    def upsert_resources(self, resources: list[dict[str, object]]) -> None:
        connection = self._tx()
        try:
            now = time.time()
            for item in resources:
                connection.execute(
                    "INSERT INTO host_resources(id,kind,tags_json,enabled,updated_at) VALUES(?,?,?,?,?) "
                    "ON CONFLICT(id) DO UPDATE SET kind=excluded.kind,tags_json=excluded.tags_json,enabled=excluded.enabled,updated_at=excluded.updated_at",
                    (str(item["id"]), str(item.get("kind", "accelerator")), canonical_json(item.get("tags", {})), int(item.get("enabled", True)), now),
                )
            connection.commit()
        finally:
            connection.close()

    def _sweep_locked(self, connection: sqlite3.Connection, stale_seconds: float = 30.0) -> None:
        cutoff = time.time() - stale_seconds
        for owner in connection.execute("SELECT * FROM host_owners WHERE state IN ('active','intent') AND heartbeat_at<?", (cutoff,)).fetchall():
            if _alive(owner["pid"], owner["process_start"]):
                continue
            self._release_locked(connection, str(owner["id"]), "stale")
        connection.execute(
            "UPDATE host_foreground_intents SET state='released',heartbeat_at=? WHERE state='active' "
            "AND owner_id IN (SELECT id FROM host_owners WHERE state NOT IN ('active','intent'))",
            (time.time(),),
        )

    @staticmethod
    def _request_ids(request: dict[str, object]) -> list[str]:
        return [str(item) for item in request.get("ids", [])]

    @staticmethod
    def _extra_ids(request: dict[str, object], selected: list[sqlite3.Row]) -> list[str]:
        extra = [str(item) for item in request.get("exclusive_resources", [])]
        if request.get("isolate_pcie_root"):
            extra.extend(f"interference:pcie:{json.loads(row['tags_json']).get('pcie_root')}" for row in selected if json.loads(row["tags_json"]).get("pcie_root"))
        if request.get("isolate_nvlink_domain"):
            extra.extend(f"interference:nvlink:{json.loads(row['tags_json']).get('nvlink_domain')}" for row in selected if json.loads(row["tags_json"]).get("nvlink_domain"))
        return sorted(set(extra))

    @staticmethod
    def _active_resource_ids(connection: sqlite3.Connection) -> set[str]:
        reserved = {str(row[0]) for row in connection.execute("SELECT resource_id FROM host_reservations WHERE state='active'")}
        for row in connection.execute("SELECT resources_json FROM host_foreground_intents WHERE state='active'"):
            reserved.update(str(item) for item in json.loads(row[0]))
        return reserved

    @staticmethod
    def _cpu_threads(request: dict[str, object]) -> int:
        declared = int(request.get("cpu_threads", 0) or 0)
        return declared or (max(1, int(cpu_capacity() * 0.75)) if request.get("cpu_heavy") else 0)

    @staticmethod
    def _pressure_available(connection: sqlite3.Connection, request: dict[str, object]) -> bool:
        active = connection.execute(
            "SELECT COALESCE(SUM(cpu_threads),0),COALESCE(SUM(ram_bytes),0) FROM host_owners WHERE state IN ('active','intent')"
        ).fetchone()
        cpu_limit = max(1, int(cpu_capacity() * 0.75))
        ram_limit = max(0, int(memory_capacity_bytes() * 0.80))
        return int(active[0]) + HostCoordinator._cpu_threads(request) <= cpu_limit and int(active[1]) + int(request.get("ram_bytes", 0) or 0) <= ram_limit

    def _select_locked(self, connection: sqlite3.Connection, request: dict[str, object]) -> list[str] | None:
        if not self._pressure_available(connection, request):
            return None
        kind = str(request.get("kind", "accelerator"))
        rows = connection.execute("SELECT * FROM host_resources WHERE enabled=1 AND kind=? ORDER BY id", (kind,)).fetchall()
        tags = {str(key): str(value) for key, value in dict(request.get("tags", {})).items()}
        rows = [row for row in rows if all(str(json.loads(row["tags_json"]).get(key)) == value for key, value in tags.items())]
        requested_ids = self._request_ids(request)
        count = int(request.get("count", 0) or 0)
        if requested_ids:
            selected = [row for row in rows if row["id"] in requested_ids]
            combinations = [tuple(selected)] if len(selected) == len(requested_ids) else []
        elif count:
            combinations = itertools.combinations(rows, count)
        else:
            combinations = [tuple()]
        active = self._active_resource_ids(connection)
        for combination in combinations:
            resource_ids = [str(row["id"]) for row in combination]
            expanded = sorted(set(resource_ids + self._extra_ids(request, list(combination))))
            if not active.intersection(expanded):
                return expanded
        return None

    def _candidate_resources_locked(self, connection: sqlite3.Connection,
                                    request: dict[str, object]) -> list[list[str]]:
        """Return runtime-discovered candidate bundles, including occupied ones."""
        kind = str(request.get("kind", "accelerator"))
        rows = connection.execute("SELECT * FROM host_resources WHERE enabled=1 AND kind=? ORDER BY id", (kind,)).fetchall()
        tags = {str(key): str(value) for key, value in dict(request.get("tags", {})).items()}
        rows = [row for row in rows if all(str(json.loads(row["tags_json"]).get(key)) == value for key, value in tags.items())]
        requested_ids = self._request_ids(request)
        count = int(request.get("count", 0) or 0)
        if requested_ids:
            selected = [row for row in rows if row["id"] in requested_ids]
            combinations = [tuple(selected)] if len(selected) == len(requested_ids) else []
        elif count:
            combinations = itertools.combinations(rows, count)
        else:
            combinations = [tuple()]
        return [
            sorted(set([str(row["id"]) for row in combination] + self._extra_ids(request, list(combination))))
            for combination in combinations
        ]

    @staticmethod
    def _conflicting_owners_locked(connection: sqlite3.Connection, resources: list[str]) -> list[sqlite3.Row]:
        if not resources:
            return []
        marks = ",".join("?" for _ in resources)
        return connection.execute(
            f"SELECT DISTINCT o.* FROM host_owners o JOIN host_reservations r ON r.owner_id=o.id "
            f"WHERE o.state='active' AND r.state='active' AND r.resource_id IN ({marks})",
            resources,
        ).fetchall()

    def _request_preemption_locked(self, connection: sqlite3.Connection,
                                   request: dict[str, object], priority_class: str) -> list[str]:
        """Signal one viable lower-priority bundle, preferring the fewest victims."""
        requester = _priority_value(priority_class)
        candidates: list[tuple[int, int, list[str], list[sqlite3.Row]]] = []
        for resources in self._candidate_resources_locked(connection, request):
            owners = self._conflicting_owners_locked(connection, resources)
            if owners and all(bool(row["preemptible"]) and _priority_value(str(row["priority_class"])) < requester for row in owners):
                candidates.append((len(owners), sum(_priority_value(str(row["priority_class"])) for row in owners), resources, owners))
        if not candidates:
            return []
        _, _, resources, owners = min(candidates, key=lambda item: (item[0], item[1], item[2]))
        now = time.time()
        for owner in owners:
            connection.execute("UPDATE host_owners SET preempt_requested=1,heartbeat_at=? WHERE id=?", (now, owner["id"]))
        return resources

    def _reserve_locked(self, connection: sqlite3.Connection, *, owner_id: str,
                        owner_kind: str, project_root: str | Path,
                        request: dict[str, object], pid: int,
                        priority_class: str, job_id: str | None = None,
                        attempt_id: str | None = None, service_id: str | None = None) -> tuple[str, list[str]] | None:
        priority_class = _normalize_priority_class(priority_class)
        resources = self._select_locked(connection, request)
        if resources is None:
            self._request_preemption_locked(connection, request, priority_class)
            return None
        now = time.time()
        connection.execute(
            "INSERT INTO host_owners(id,owner_kind,project_root,job_id,attempt_id,service_id,pid,process_start,state,"
            "priority_class,preemptible,cpu_threads,ram_bytes,acquired_at,heartbeat_at) "
            "VALUES(?,?,?,?,?,?,?,?,'active',?,1,?,?,?,?)",
            (owner_id, owner_kind, str(Path(project_root).resolve()), job_id, attempt_id, service_id,
             pid, _process_start(pid), priority_class, self._cpu_threads(request),
             int(request.get("ram_bytes", 0) or 0), now, now),
        )
        for resource_id in resources:
            connection.execute(
                "INSERT INTO host_reservations(resource_id,owner_id,state,acquired_at,heartbeat_at) VALUES(?,?,'active',?,?)",
                (resource_id, owner_id, now, now),
            )
        return owner_id, [item for item in resources if item.startswith("accelerator:")]

    def reserve_background(self, *, project_root: str | Path, job_id: str, attempt_id: str,
                           request: dict[str, object], pid: int) -> tuple[str, list[str]] | None:
        owner_id = background_owner_id(project_root, job_id, attempt_id)
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            reserved = self._reserve_locked(
                connection, owner_id=owner_id, owner_kind="background", project_root=project_root,
                request=request, pid=pid, priority_class="background_cuda", job_id=job_id,
                attempt_id=attempt_id,
            )
            connection.commit()
            return reserved
        except sqlite3.IntegrityError:
            connection.rollback()
            return None
        finally:
            connection.close()

    def reserve_service(self, *, project_root: str | Path, service_id: str,
                        request: dict[str, object], pid: int,
                        priority_class: str = "idle_model_residency") -> tuple[str, list[str]] | None:
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            owner_id = f"service:{digest(str(Path(project_root).resolve()))[:16]}:{service_id}:{uuid.uuid4()}"
            reserved = self._reserve_locked(
                connection, owner_id=owner_id, owner_kind="service", project_root=project_root,
                request=request, pid=pid, priority_class=priority_class, service_id=service_id,
            )
            connection.commit()
            return reserved
        except sqlite3.IntegrityError:
            connection.rollback()
            return None
        finally:
            connection.close()

    def set_priority(self, owner_id: str, priority_class: str) -> bool:
        priority_class = _normalize_priority_class(priority_class)
        connection = self._tx()
        try:
            row = connection.execute("SELECT state,preempt_requested FROM host_owners WHERE id=?", (owner_id,)).fetchone()
            if row is None or row["state"] != "active" or bool(row["preempt_requested"]):
                connection.commit()
                return False
            connection.execute("UPDATE host_owners SET priority_class=?,heartbeat_at=? WHERE id=?", (priority_class, time.time(), owner_id))
            connection.commit()
            return True
        finally:
            connection.close()

    def request_preemption(self, owner_id: str) -> bool:
        connection = self._tx()
        try:
            changed = connection.execute(
                "UPDATE host_owners SET preempt_requested=1,heartbeat_at=? "
                "WHERE id=? AND state='active' AND preemptible=1",
                (time.time(), owner_id),
            ).rowcount
            connection.commit()
            return bool(changed)
        finally:
            connection.close()

    def owner(self, owner_id: str) -> dict[str, object] | None:
        try:
            connection = self.connect(readonly=True)
        except sqlite3.Error:
            return None
        try:
            row = connection.execute("SELECT * FROM host_owners WHERE id=?", (owner_id,)).fetchone()
            if row is None:
                return None
            resources = [str(item[0]) for item in connection.execute(
                "SELECT resource_id FROM host_reservations WHERE owner_id=? AND state='active' ORDER BY resource_id", (owner_id,)
            )]
            return {key: row[key] for key in row.keys()} | {"resources": resources}
        finally:
            connection.close()

    def begin_foreground(self, *, project_root: str | Path, request: dict[str, object], pid: int,
                         priority_class: str = "foreground_gpu") -> tuple[str, list[str]]:
        priority_class = _normalize_priority_class(priority_class)
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            resources = self._select_locked(connection, request)
            if resources is None:
                resources = self._request_preemption_locked(connection, request, priority_class)
                if not resources:
                    candidates = self._candidate_resources_locked(connection, request)
                    resources = candidates[0] if candidates else []
            owner_id = f"foreground:{uuid.uuid4()}"
            intent_id = str(uuid.uuid4())
            now = time.time()
            cpu_threads = int(request.get("cpu_threads", 0) or 0)
            ram_bytes = int(request.get("ram_bytes", 0) or 0)
            connection.execute(
                "INSERT INTO host_owners(id,owner_kind,project_root,pid,process_start,state,priority_class,preemptible,cpu_threads,ram_bytes,acquired_at,heartbeat_at) VALUES(?,?,?,?,?,'intent',?,0,?,?,?,?)",
                (owner_id, "foreground", str(Path(project_root).resolve()), pid, _process_start(pid), priority_class, cpu_threads, ram_bytes, now, now),
            )
            connection.execute(
                "INSERT INTO host_foreground_intents(id,owner_id,resources_json,cpu_threads,ram_bytes,state,created_at,heartbeat_at) VALUES(?,?,?,?,?,'active',?,?)",
                (intent_id, owner_id, canonical_json(resources), cpu_threads, ram_bytes, now, now),
            )
            active_cpu, active_ram = connection.execute(
                "SELECT COALESCE(SUM(cpu_threads),0),COALESCE(SUM(ram_bytes),0) "
                "FROM host_owners WHERE state='active'"
            ).fetchone()
            pressure_conflict = int(active_cpu) + cpu_threads > max(1, int(cpu_capacity() * 0.75)) or int(active_ram) + ram_bytes > int(memory_capacity_bytes() * 0.80)
            for owner in connection.execute("SELECT * FROM host_owners WHERE state='active'").fetchall():
                held = {str(row[0]) for row in connection.execute("SELECT resource_id FROM host_reservations WHERE owner_id=? AND state='active'", (owner["id"],))}
                if bool(owner["preemptible"]) and _priority_value(str(owner["priority_class"])) < _priority_value(priority_class) and (pressure_conflict or held.intersection(resources)):
                    connection.execute("UPDATE host_owners SET preempt_requested=1,heartbeat_at=? WHERE id=?", (now, owner["id"]))
            connection.commit()
            return owner_id, resources
        finally:
            connection.close()

    def activate_foreground(self, owner_id: str, resources: list[str]) -> bool:
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            if any(connection.execute("SELECT 1 FROM host_reservations WHERE resource_id=? AND state='active'", (item,)).fetchone() for item in resources):
                connection.commit()
                return False
            now = time.time()
            for item in resources:
                connection.execute("INSERT INTO host_reservations(resource_id,owner_id,state,acquired_at,heartbeat_at) VALUES(?,?,'active',?,?)", (item, owner_id, now, now))
            connection.execute("UPDATE host_owners SET state='active',heartbeat_at=? WHERE id=?", (now, owner_id))
            connection.commit()
            return True
        except sqlite3.IntegrityError:
            connection.rollback()
            return False
        finally:
            connection.close()

    def conflicts(self, resources: list[str]) -> list[str]:
        connection = self.connect(readonly=True)
        try:
            if not resources:
                return []
            marks = ",".join("?" for _ in resources)
            return [str(row[0]) for row in connection.execute(
                f"SELECT DISTINCT owner_id FROM host_reservations WHERE state='active' AND resource_id IN ({marks}) AND owner_id IN "
                "(SELECT id FROM host_owners WHERE state='active')", resources
            )]
        finally:
            connection.close()

    def heartbeat(self, owner_id: str, pid: int | None = None) -> None:
        connection = self._tx()
        try:
            now = time.time()
            connection.execute("UPDATE host_owners SET heartbeat_at=?,pid=COALESCE(?,pid),process_start=COALESCE(?,process_start) WHERE id=?", (now, pid, _process_start(pid) if pid else None, owner_id))
            connection.execute("UPDATE host_reservations SET heartbeat_at=? WHERE owner_id=? AND state='active'", (now, owner_id))
            connection.commit()
        finally:
            connection.close()

    def preempt_requested(self, owner_id: str) -> bool:
        try:
            connection = self.connect(readonly=True)
        except sqlite3.Error:
            return False
        try:
            row = connection.execute("SELECT preempt_requested FROM host_owners WHERE id=? AND state='active'", (owner_id,)).fetchone()
            return bool(row and row[0])
        finally:
            connection.close()

    def _release_locked(self, connection: sqlite3.Connection, owner_id: str, state: str = "released") -> None:
        now = time.time()
        connection.execute("UPDATE host_reservations SET state='released',heartbeat_at=? WHERE owner_id=? AND state='active'", (now, owner_id))
        connection.execute("UPDATE host_owners SET state=?,heartbeat_at=? WHERE id=?", (state, now, owner_id))
        connection.execute("UPDATE host_foreground_intents SET state='released',heartbeat_at=? WHERE owner_id=? AND state='active'", (now, owner_id))

    def release(self, owner_id: str) -> None:
        connection = self._tx()
        try:
            self._release_locked(connection, owner_id)
            connection.commit()
        finally:
            connection.close()
