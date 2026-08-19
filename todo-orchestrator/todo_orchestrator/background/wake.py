"""Best-effort zero-output wake hook used after successful todo commits."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

from .store import runtime_paths


def _worker_is_live(database: Path) -> bool:
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=0.05)
        try:
            rows = connection.execute(
                "SELECT pid,process_start FROM background_workers WHERE state='running' AND heartbeat_at>?",
                (time.time() - 30.0,),
            ).fetchall()
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return False
    for pid, expected_start in rows:
        try:
            actual_start = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()[21]
        except (OSError, IndexError):
            continue
        if not expected_start or expected_start == actual_start:
            return True
    return False


def watch_is_armed(project_root: str | Path) -> bool:
    database = runtime_paths(project_root).database
    if not database.exists():
        return False
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True, timeout=0.05)
        try:
            return connection.execute("SELECT 1 FROM background_watches WHERE state='armed' LIMIT 1").fetchone() is not None
        finally:
            connection.close()
    except (OSError, sqlite3.Error):
        return False


def wake_worker(project_root: str | Path) -> bool:
    root = Path(project_root).resolve()
    paths = runtime_paths(root)
    if not watch_is_armed(root):
        return False
    paths.root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(paths.wake_lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            import fcntl
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (ImportError, BlockingIOError):
            return False
        if _worker_is_live(paths.database):
            return True
        environment = os.environ.copy()
        package_root = str(Path(__file__).resolve().parents[2])
        environment["PYTHONPATH"] = package_root + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
        process = subprocess.Popen(
            [sys.executable, "-m", "todo_orchestrator.background.worker", "--project", str(root)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True, env=environment,
        )
        process.returncode = 0
        deadline = time.monotonic() + 1.0
        while time.monotonic() < deadline:
            if _worker_is_live(paths.database):
                break
            time.sleep(0.025)
        return True
    except Exception:
        return False
    finally:
        os.close(descriptor)


def wake_after_commit(project_root: str | Path, revision: int) -> None:
    del revision
    try:
        wake_worker(project_root)
    except Exception:
        pass
