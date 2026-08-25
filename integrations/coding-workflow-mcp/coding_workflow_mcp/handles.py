"""Owner-only opaque capability aliases; never a work-state authority."""

from __future__ import annotations

import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import time
from typing import Any
from contextlib import closing


WORKFLOW_PREFIX = "wf_"
DELEGATION_PREFIX = "dg_"
DIAGNOSTIC_PREFIX = "diag_"
DEFAULT_WORKFLOW_TTL = 24 * 60 * 60
DEFAULT_DELEGATION_TTL = 6 * 60 * 60
TERMINAL_DELEGATION_TTL = 15 * 60


class InvalidHandle(ValueError):
    """Raised when a capability is unknown, expired, or the wrong kind."""


def default_state_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local" / "state") / "coding-workflow-mcp"


def _capability(prefix: str) -> str:
    # token_urlsafe(32) contains 256 random bits, exceeding the 192-bit floor.
    return prefix + secrets.token_urlsafe(32)


class CapabilityStore:
    """Concurrent SQLite alias store containing capabilities and bounded diagnostics."""

    def __init__(self, state_dir: str | os.PathLike[str] | None = None) -> None:
        self.state_dir = Path(state_dir) if state_dir is not None else default_state_dir()
        self.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.state_dir, 0o700)
        self.db_path = self.state_dir / "capabilities.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _secure_database_files(self) -> None:
        for path in (self.db_path, Path(str(self.db_path) + "-wal"), Path(str(self.db_path) + "-shm")):
            try:
                os.chmod(path, 0o600)
            except FileNotFoundError:
                # SQLite may remove transient WAL/SHM files between discovery
                # and chmod when several bridge processes initialize together.
                pass

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS capabilities (
                    handle TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(kind IN ('workflow', 'delegation')),
                    repo TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    terminal INTEGER NOT NULL DEFAULT 0 CHECK(terminal IN (0, 1))
                );
                CREATE INDEX IF NOT EXISTS capabilities_expiry
                    ON capabilities(expires_at);
                CREATE TABLE IF NOT EXISTS diagnostics (
                    diagnostic_id TEXT PRIMARY KEY,
                    message TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS diagnostics_expiry
                    ON diagnostics(expires_at);
                """
            )
        self._secure_database_files()
        self.sweep()

    @staticmethod
    def _canonical_repo(payload: dict[str, Any]) -> str:
        repo = payload.get("repo")
        if not isinstance(repo, str) or not repo or not Path(repo).is_absolute():
            raise ValueError("capability payload requires an absolute canonical repo")
        return str(Path(repo).resolve())

    def _create(self, kind: str, prefix: str, payload: dict[str, Any], ttl: float) -> str:
        repo = self._canonical_repo(payload)
        now = time.time()
        for _ in range(3):
            handle = _capability(prefix)
            try:
                with closing(self._connect()) as connection:
                    connection.execute("BEGIN IMMEDIATE")
                    connection.execute(
                        "INSERT INTO capabilities VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                        (handle, kind, repo, json.dumps(payload, separators=(",", ":")), now, now, now + ttl),
                    )
                    connection.commit()
                self._secure_database_files()
                return handle
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("unable to allocate capability")

    def create_workflow(self, payload: dict[str, Any], ttl: float = DEFAULT_WORKFLOW_TTL) -> str:
        return self._create("workflow", WORKFLOW_PREFIX, payload, ttl)

    def find_workflows(
        self,
        repo: str | os.PathLike[str],
        task_id: str,
        project_uuid: str | None,
        *,
        limit: int = 32,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Return bounded facade-owned candidates for explicit claim recovery."""
        canonical_repo = str(Path(repo).resolve())
        now = time.time()
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT handle, payload
                FROM capabilities
                WHERE kind='workflow' AND repo=? AND expires_at>?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (canonical_repo, now, max(1, min(limit, 100))),
            ).fetchall()
        matches: list[tuple[str, dict[str, Any]]] = []
        for row in rows:
            try:
                payload = json.loads(str(row["payload"]))
            except (TypeError, json.JSONDecodeError):
                continue
            if payload.get("task_id") != task_id:
                continue
            if project_uuid and payload.get("project_uuid") != project_uuid:
                continue
            matches.append((str(row["handle"]), payload))
        return matches

    def reissue_workflow(
        self,
        handle: str,
        payload: dict[str, Any],
        ttl: float = DEFAULT_WORKFLOW_TTL,
    ) -> str:
        """Atomically add a fresh alias after its stored claim is revalidated."""
        repo = self._canonical_repo(payload)
        now = time.time()
        replacement = _capability(WORKFLOW_PREFIX)
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT kind, expires_at, payload FROM capabilities WHERE handle=?",
                (handle,),
            ).fetchone()
            if row is None or row["kind"] != "workflow" or float(row["expires_at"]) <= now:
                connection.rollback()
                raise InvalidHandle("workflow capability is no longer recoverable")
            source = json.loads(str(row["payload"]))
            identity_keys = ("repo", "project_uuid", "task_id", "claim_token")
            if any(source.get(key) != payload.get(key) for key in identity_keys):
                connection.rollback()
                raise InvalidHandle("workflow capability identity changed")
            connection.execute(
                "INSERT INTO capabilities VALUES (?, 'workflow', ?, ?, ?, ?, ?, 0)",
                (
                    replacement,
                    repo,
                    json.dumps(payload, separators=(",", ":")),
                    now,
                    now,
                    now + ttl,
                ),
            )
            connection.commit()
        self._secure_database_files()
        return replacement

    def delete_workflow_family(self, payload: dict[str, Any]) -> int:
        """Remove every alias for one terminal facade-owned todo claim."""
        repo = self._canonical_repo(payload)
        project_uuid, task_id, claim_token = (
            payload.get(key) for key in ("project_uuid", "task_id", "claim_token")
        )
        if not all(
            isinstance(value, str) and value
            for value in (project_uuid, task_id, claim_token)
        ):
            raise ValueError("workflow family requires a complete claim identity")
        lineage = {
            value for value in payload.get("lineage_fingerprints", [])
            if isinstance(value, str) and value
        }
        if isinstance(payload.get("claim_fingerprint"), str):
            lineage.add(payload["claim_fingerprint"])
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT handle, payload FROM capabilities WHERE kind='workflow' AND repo=?",
                (repo,),
            ).fetchall()
            handles: list[tuple[str]] = []
            for row in rows:
                try:
                    candidate = json.loads(str(row["payload"]))
                except (TypeError, json.JSONDecodeError):
                    continue
                if (
                    candidate.get("project_uuid") != project_uuid
                    or candidate.get("task_id") != task_id
                ):
                    continue
                candidate_lineage = {
                    value for value in candidate.get("lineage_fingerprints", [])
                    if isinstance(value, str) and value
                }
                if isinstance(candidate.get("claim_fingerprint"), str):
                    candidate_lineage.add(candidate["claim_fingerprint"])
                if candidate.get("claim_token") == claim_token or lineage.intersection(candidate_lineage):
                    handles.append((str(row["handle"]),))
            connection.executemany("DELETE FROM capabilities WHERE handle=?", handles)
            connection.commit()
        return len(handles)

    def create_delegation(self, payload: dict[str, Any], ttl: float = DEFAULT_DELEGATION_TTL) -> str:
        return self._create("delegation", DELEGATION_PREFIX, payload, ttl)

    def _get(self, handle: str, kind: str) -> dict[str, Any]:
        expected_prefix = WORKFLOW_PREFIX if kind == "workflow" else DELEGATION_PREFIX
        if not isinstance(handle, str) or not handle.startswith(expected_prefix):
            raise InvalidHandle("invalid capability")
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload, expires_at FROM capabilities WHERE handle=? AND kind=?",
                (handle, kind),
            ).fetchone()
        if row is None:
            raise InvalidHandle("unknown capability")
        if float(row["expires_at"]) <= time.time():
            self.delete(handle)
            raise InvalidHandle("expired capability")
        value = json.loads(str(row["payload"]))
        if str(Path(value["repo"]).resolve()) != value["repo"]:
            raise InvalidHandle("invalid repository identity")
        return value

    def get_workflow(self, handle: str) -> dict[str, Any]:
        return self._get(handle, "workflow")

    def get_delegation(self, handle: str) -> dict[str, Any]:
        return self._get(handle, "delegation")

    def update(self, handle: str, payload: dict[str, Any], *, terminal: bool = False) -> None:
        repo = self._canonical_repo(payload)
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT kind FROM capabilities WHERE handle=?", (handle,)).fetchone()
            if row is None:
                raise InvalidHandle("unknown capability")
            if terminal and row["kind"] == "delegation":
                ttl = TERMINAL_DELEGATION_TTL
            elif row["kind"] == "workflow":
                ttl = DEFAULT_WORKFLOW_TTL
            else:
                ttl = DEFAULT_DELEGATION_TTL
            expires = now + ttl
            connection.execute(
                "UPDATE capabilities SET repo=?, payload=?, updated_at=?, expires_at=?, terminal=? WHERE handle=?",
                (repo, json.dumps(payload, separators=(",", ":")), now, expires, int(terminal), handle),
            )
            connection.commit()
        self._secure_database_files()

    def delete(self, handle: str) -> None:
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM capabilities WHERE handle=?", (handle,))
            connection.commit()

    def write_diagnostic(self, message: str, ttl: float = 24 * 60 * 60) -> str:
        diagnostic_id = _capability(DIAGNOSTIC_PREFIX)
        now = time.time()
        # Diagnostics are bounded and must already be redacted by the caller.
        bounded = message[-16_384:]
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "INSERT INTO diagnostics VALUES (?, ?, ?, ?)",
                (diagnostic_id, bounded, now, now + ttl),
            )
            connection.commit()
        self._secure_database_files()
        return diagnostic_id

    def sweep(self, limit: int = 100) -> dict[str, int]:
        now = time.time()
        with closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            capabilities = connection.execute(
                "SELECT handle FROM capabilities WHERE expires_at <= ? ORDER BY expires_at LIMIT ?",
                (now, max(1, limit)),
            ).fetchall()
            diagnostics = connection.execute(
                "SELECT diagnostic_id FROM diagnostics WHERE expires_at <= ? ORDER BY expires_at LIMIT ?",
                (now, max(1, limit)),
            ).fetchall()
            connection.executemany("DELETE FROM capabilities WHERE handle=?", capabilities)
            connection.executemany("DELETE FROM diagnostics WHERE diagnostic_id=?", diagnostics)
            connection.commit()
        return {"capabilities": len(capabilities), "diagnostics": len(diagnostics)}

    def permissions(self) -> tuple[int, int]:
        return stat.S_IMODE(self.state_dir.stat().st_mode), stat.S_IMODE(self.db_path.stat().st_mode)
