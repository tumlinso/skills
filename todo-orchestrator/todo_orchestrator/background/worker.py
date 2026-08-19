"""Self-terminating local supervisor for the private background queue."""

from __future__ import annotations

import argparse
import concurrent.futures
import os
import time

from .runner import run_job
from .host import HostCoordinator
from .scheduler import claim_runnable, dispatch_watch_handlers
from .store import BackgroundStore


def _execute(store: BackgroundStore, worker_id: str, claimed) -> None:
    job, attempt_id = claimed
    try:
        outcome = run_job(store, worker_id, job, attempt_id)
    except Exception as error:
        outcome = {
            "state": "failed", "returncode": None, "reason": "runner-exception",
            "stdout_path": "", "stderr_path": "", "stdout_tail": "", "stderr_tail": str(error)[-1000:],
            "metadata": {"error": type(error).__name__},
            "result": {"valid": False, "status": "failed", "classification": "background-command-failure", "severity": 0},
        }
    try:
        store.finish(str(job["id"]), attempt_id, **outcome)
    finally:
        if job.get("host_owner_id"):
            HostCoordinator().release(str(job["host_owner_id"]))


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--project", required=True)
    parser.add_argument("--idle-seconds", type=float, default=float(os.environ.get("TODO_BACKGROUND_IDLE_SECONDS", "15")))
    parser.add_argument("--max-children", type=int, default=int(os.environ.get("TODO_BACKGROUND_MAX_CHILDREN", "4")))
    args = parser.parse_args()
    store = BackgroundStore(args.project)
    worker_id = store.register_worker()
    idle_since = time.monotonic()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_children), thread_name_prefix="todo-background")
    active: set[concurrent.futures.Future] = set()
    try:
        while True:
            store.heartbeat(worker_id)
            dispatch_watch_handlers(store)
            done = {future for future in active if future.done()}
            for future in done:
                active.remove(future)
                future.result()
            launched = False
            while len(active) < max(1, args.max_children):
                claimed = claim_runnable(store, worker_id)
                if not claimed:
                    break
                active.add(executor.submit(_execute, store, worker_id, claimed))
                launched = True
            if not active and not launched:
                if time.monotonic() - idle_since >= args.idle_seconds:
                    return 0
                time.sleep(0.25)
                continue
            idle_since = time.monotonic()
            time.sleep(0.1)
    finally:
        executor.shutdown(wait=True, cancel_futures=False)
        store.stop_worker(worker_id)


if __name__ == "__main__":
    raise SystemExit(main())
