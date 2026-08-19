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


SCHEMA = """
CREATE TABLE IF NOT EXISTS host_resources(
 id TEXT PRIMARY KEY, kind TEXT NOT NULL, tags_json TEXT NOT NULL,
 enabled INTEGER NOT NULL DEFAULT 1, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS host_owners(
 id TEXT PRIMARY KEY, owner_kind TEXT NOT NULL, project_root TEXT,
 job_id TEXT, attempt_id TEXT, pid INTEGER, process_start TEXT,
 state TEXT NOT NULL, preempt_requested INTEGER NOT NULL DEFAULT 0,
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

    def reserve_background(self, *, project_root: str | Path, job_id: str, attempt_id: str,
                           request: dict[str, object], pid: int) -> tuple[str, list[str]] | None:
        owner_id = background_owner_id(project_root, job_id, attempt_id)
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            resources = self._select_locked(connection, request)
            if resources is None:
                connection.commit()
                return None
            now = time.time()
            connection.execute(
                "INSERT INTO host_owners(id,owner_kind,project_root,job_id,attempt_id,pid,process_start,state,cpu_threads,ram_bytes,acquired_at,heartbeat_at) "
                "VALUES(?,?,?,?,?,?,?,'active',?,?,?,?)",
                (owner_id, "background", str(Path(project_root).resolve()), job_id, attempt_id, pid, _process_start(pid),
                 self._cpu_threads(request), int(request.get("ram_bytes", 0) or 0), now, now),
            )
            for resource_id in resources:
                connection.execute("INSERT INTO host_reservations(resource_id,owner_id,state,acquired_at,heartbeat_at) VALUES(?,?,'active',?,?)", (resource_id, owner_id, now, now))
            connection.commit()
            return owner_id, [item for item in resources if item.startswith("accelerator:")]
        except sqlite3.IntegrityError:
            connection.rollback()
            return None
        finally:
            connection.close()

    def begin_foreground(self, *, project_root: str | Path, request: dict[str, object], pid: int) -> tuple[str, list[str]]:
        connection = self._tx()
        try:
            self._sweep_locked(connection)
            resources = self._select_locked(connection, request)
            if resources is None:
                # Preserve exact requested physical scope while intent drains conflicts.
                requested = self._request_ids(request)
                selected = connection.execute(
                    f"SELECT * FROM host_resources WHERE id IN ({','.join('?' for _ in requested)})", requested
                ).fetchall() if requested else []
                resources = sorted(set(requested + self._extra_ids(request, selected)))
            owner_id = f"foreground:{uuid.uuid4()}"
            intent_id = str(uuid.uuid4())
            now = time.time()
            cpu_threads = int(request.get("cpu_threads", 0) or 0)
            ram_bytes = int(request.get("ram_bytes", 0) or 0)
            connection.execute(
                "INSERT INTO host_owners(id,owner_kind,project_root,pid,process_start,state,cpu_threads,ram_bytes,acquired_at,heartbeat_at) VALUES(?,?,?,?,?,'intent',?,?,?,?)",
                (owner_id, "foreground", str(Path(project_root).resolve()), pid, _process_start(pid), cpu_threads, ram_bytes, now, now),
            )
            connection.execute(
                "INSERT INTO host_foreground_intents(id,owner_id,resources_json,cpu_threads,ram_bytes,state,created_at,heartbeat_at) VALUES(?,?,?,?,?,'active',?,?)",
                (intent_id, owner_id, canonical_json(resources), cpu_threads, ram_bytes, now, now),
            )
            active_cpu, active_ram = connection.execute(
                "SELECT COALESCE(SUM(cpu_threads),0),COALESCE(SUM(ram_bytes),0) FROM host_owners WHERE state='active' AND owner_kind='background'"
            ).fetchone()
            pressure_conflict = int(active_cpu) + cpu_threads > max(1, int(cpu_capacity() * 0.75)) or int(active_ram) + ram_bytes > int(memory_capacity_bytes() * 0.80)
            for owner in connection.execute("SELECT id FROM host_owners WHERE state='active' AND owner_kind='background'").fetchall():
                held = {str(row[0]) for row in connection.execute("SELECT resource_id FROM host_reservations WHERE owner_id=? AND state='active'", (owner["id"],))}
                if pressure_conflict or held.intersection(resources):
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
                "(SELECT id FROM host_owners WHERE owner_kind='background' AND state='active')", resources
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
