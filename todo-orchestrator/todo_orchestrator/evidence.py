"""Gate input fingerprints and evidence metadata."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .git_state import dirty_paths, file_hash, git_head


def gate_input_fingerprint(conn: sqlite3.Connection, repo_root: Path, config: dict[str, object]) -> tuple[str, dict[str, object]]:
    files: list[dict[str, str]] = []
    for value in sorted(str(item) for item in config.get("input_paths", [])):
        path = repo_root / value
        files.append({"path": value, "sha256": file_hash(path) if path.is_file() else "missing"})
    interfaces = []
    for interface_id in sorted(str(item) for item in config.get("interfaces", [])):
        row = conn.execute("SELECT id,state,version,content_hash FROM interfaces WHERE id=?", (interface_id,)).fetchone()
        interfaces.append(dict(row) if row else {"id": interface_id, "state": "missing"})
    command_contract = {
        key: config.get(key)
        for key in (
            "argv", "cwd", "env", "timeout", "expected_exit_code", "metric_file", "metric_path",
            "cuda", "operator", "threshold", "evaluation_required", "path", "pattern", "task_id", "status",
            "result", "checkpoint_id", "interface_id", "state", "version", "accepted", "resources", "locks",
        )
        if key in config
    }
    semantic = {"files": files, "interfaces": interfaces, "command_contract": command_contract}
    if config.get("track_git_head"):
        semantic["git_head"] = git_head(repo_root)
    current_dirty = dirty_paths(repo_root)
    payload = {
        **semantic,
        "recorded_git_head": git_head(repo_root),
        "dirty_paths": current_dirty,
        "diff_fingerprint": hashlib.sha256(json.dumps(current_dirty, sort_keys=True).encode()).hexdigest(),
    }
    return hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest(), payload


def gate_is_satisfied(row: sqlite3.Row) -> bool:
    return bool(row["valid"] and row["status"] in {"passed", "evaluated_not_promoted"})


def required_gates(conn: sqlite3.Connection, task_id: str) -> list[dict[str, object]]:
    return [dict(row) for row in conn.execute("SELECT * FROM gates WHERE task_id=? AND required=1 ORDER BY id", (task_id,))]
