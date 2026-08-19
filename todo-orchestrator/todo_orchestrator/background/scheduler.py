"""Small private scheduler: event handlers, host headroom, and one job claim."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from .resources import background_launch_allowed


def dispatch_watch_handlers(store) -> None:
    for watch in store.watches("armed"):
        private = watch["spec"].get("_runtime", {})
        argv = private.get("event_handler_argv") if isinstance(private, dict) else None
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            continue
        try:
            subprocess.run(argv, cwd=watch["project_root"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue


def claim_runnable(store, worker_id: str):
    claimed = store.claim(worker_id)
    if not claimed:
        return None
    job, attempt_id = claimed
    if background_launch_allowed(dict(job.get("resources", {}))):
        return job, attempt_id
    store.finish(str(job["id"]), attempt_id, state="preempted", returncode=None, reason="foreground-host-headroom",
                 stdout_path="", stderr_path="", stdout_tail="", stderr_tail="",
                 metadata={"deferred": True}, result=None)
    return None
