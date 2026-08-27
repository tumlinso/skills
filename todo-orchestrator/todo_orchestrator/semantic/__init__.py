"""Read-only semantic views over todo-orchestrator's authoritative state."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import project_paths, read_project
from ..db import Database
from .anchors import resolve_anchor
from .history import semantic_delta
from .state import semantic_state
from .workflow import workflow_state


class SemanticReader:
    """Open the existing todo database in true read-only mode."""

    def __init__(self, repo_root: str | Path = ".") -> None:
        self.paths = project_paths(repo_root)
        self.project = read_project(self.paths.repo_root)
        configuration = self.project.get("configuration", {})
        self.db = Database(
            self.paths.db_file,
            busy_timeout_ms=int(configuration.get("busy_timeout_ms", 5000)),
            read_only=True,
        )

    @staticmethod
    def _fingerprint(conn) -> str:
        """Fingerprint the transaction's logical SQLite image, including WAL data."""
        return hashlib.sha256(conn.serialize()).hexdigest()

    def state(self, **filters) -> dict[str, object]:
        with self.db.read() as conn:
            result = semantic_state(conn, self.project, **filters)
            result["read_authority_fingerprint"] = self._fingerprint(conn)
            return result

    def anchor(self, **selector) -> dict[str, object]:
        with self.db.read() as conn:
            result = resolve_anchor(conn, **selector)
            result["project_uuid"] = self.project["project_uuid"]
            result["read_authority_fingerprint"] = self._fingerprint(conn)
            return result

    def delta(self, **selector) -> dict[str, object]:
        with self.db.read() as conn:
            result = semantic_delta(conn, **selector)
            result["project_uuid"] = self.project["project_uuid"]
            result["read_authority_fingerprint"] = self._fingerprint(conn)
            return result

    def workflow(self) -> dict[str, object]:
        with self.db.read() as conn:
            result = workflow_state(conn, self.project)
            result["project_uuid"] = self.project["project_uuid"]
            result["read_authority_fingerprint"] = self._fingerprint(conn)
            return result
