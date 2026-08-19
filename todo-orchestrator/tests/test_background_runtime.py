from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

from v2_helpers import V2Repo, base_plan, safe_task

from todo_orchestrator.background.store import BackgroundStore
from todo_orchestrator.background.runner import run_job
from todo_orchestrator.background.wake import wake_worker


class BackgroundRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = V2Repo()
        self.store = BackgroundStore(self.repo.root)

    def tearDown(self) -> None:
        self.store.set_watch_state("stopped")
        self.repo.close()

    def _arm(self) -> str:
        return self.store.arm_watch({"schema_version": 1, "project_root": str(self.repo.root), "watch": {}})

    def _wait(self, predicate, timeout: float = 8.0):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(0.05)
        self.fail("timed out waiting for background runtime")

    def test_no_watch_keeps_public_mutation_silent(self) -> None:
        with mock.patch("todo_orchestrator.background.wake.subprocess.Popen") as popen:
            result = self.repo.apply(base_plan([safe_task("A", "src/a")]))
        popen.assert_not_called()
        self.assertEqual(result["project_revision"], 2)
        self.assertIn("projection", result)

    def test_armed_watch_auto_wakes_and_runs_structured_argv(self) -> None:
        watch_id = self._arm()
        job_id, created = self.store.enqueue({
            "watch_id": watch_id,
            "kind": "fake",
            "argv": [sys.executable, "-c", "import json; print(json.dumps({'valid': True, 'severity': 0}))"],
            "cwd": str(self.repo.root),
            "timeout": 5,
        })
        self.assertTrue(created)
        self.assertTrue(wake_worker(self.repo.root))
        result = self._wait(lambda: self.store.result(job_id))
        self.assertEqual(result["status"], "succeeded")
        self.assertTrue(result["valid"])

    def test_dedup_and_atomic_multi_resource_reservation(self) -> None:
        watch_id = self._arm()
        self.store.upsert_resources([
            {"id": "accelerator:GPU-a", "kind": "accelerator", "tags": {}},
            {"id": "accelerator:GPU-b", "kind": "accelerator", "tags": {}},
        ])
        spec = {"watch_id": watch_id, "kind": "fake", "argv": ["true"], "cwd": str(self.repo.root),
                "resources": {"kind": "accelerator", "ids": ["accelerator:GPU-a", "accelerator:GPU-b"]}, "dedup_key": "same"}
        first, created = self.store.enqueue(spec)
        second, duplicate = self.store.enqueue(spec)
        self.assertTrue(created)
        self.assertFalse(duplicate)
        self.assertEqual(first, second)
        claimed = self.store.claim("worker")
        self.assertEqual(set(claimed[0]["allocated_resources"]), {"accelerator:GPU-a", "accelerator:GPU-b"})
        intent = self.store.foreground_intent(["accelerator:GPU-a"])
        self.assertFalse(self.store.reserve_foreground(intent, ["accelerator:GPU-a"]))
        self.store.clear_foreground(intent)

    def test_one_supervisor_runs_independent_resources_concurrently(self) -> None:
        watch_id = self._arm()
        self.store.upsert_resources([
            {"id": "accelerator:GPU-a", "kind": "accelerator", "tags": {}},
            {"id": "accelerator:GPU-b", "kind": "accelerator", "tags": {}},
        ])
        for suffix in ("a", "b"):
            self.store.enqueue({
                "watch_id": watch_id, "kind": "parallel", "argv": [sys.executable, "-c", "import time; time.sleep(.5)"],
                "cwd": str(self.repo.root), "resources": {"ids": [f"accelerator:GPU-{suffix}"]}, "dedup_key": f"parallel-{suffix}",
            })
        self.assertTrue(wake_worker(self.repo.root))
        self._wait(lambda: all(self.store.result(row) for row in self._parallel_job_ids()))
        with self.store.connect(readonly=True) as connection:
            rows = connection.execute(
                "SELECT a.started_at,a.finished_at FROM background_attempts a JOIN background_jobs j ON j.id=a.job_id "
                "WHERE j.kind='parallel' ORDER BY a.started_at"
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertLess(rows[1]["started_at"], rows[0]["finished_at"])

    def _parallel_job_ids(self):
        with self.store.connect(readonly=True) as connection:
            return [row[0] for row in connection.execute("SELECT id FROM background_jobs WHERE kind='parallel'")]

    def test_foreground_preemption_requeues_without_retry_or_valid_result(self) -> None:
        watch_id = self._arm()
        self.store.upsert_resources([{"id": "accelerator:GPU-a", "kind": "accelerator", "tags": {}}])
        job_id, _ = self.store.enqueue({
            "watch_id": watch_id, "kind": "slow", "argv": [sys.executable, "-c", "import time; time.sleep(30)"],
            "cwd": str(self.repo.root), "timeout": 60, "retry_limit": 1,
            "resources": {"kind": "accelerator", "ids": ["accelerator:GPU-a"]},
        })
        self.assertTrue(wake_worker(self.repo.root))
        self._wait(lambda: self.store.running_conflicts(["accelerator:GPU-a"]))
        intent = self.store.foreground_intent(["accelerator:GPU-a"])
        self._wait(lambda: not self.store.running_conflicts(["accelerator:GPU-a"]))
        with self.store.connect(readonly=True) as conn:
            job = conn.execute("SELECT state,retries_used,result_id FROM background_jobs WHERE id=?", (job_id,)).fetchone()
            attempt = conn.execute("SELECT state FROM background_attempts WHERE job_id=?", (job_id,)).fetchone()
        self.assertEqual(dict(job), {"state": "queued", "retries_used": 0, "result_id": None})
        self.assertEqual(attempt["state"], "preempted")
        self.store.clear_foreground(intent)

    def test_cpu_heavy_background_yields_to_context_compiler(self) -> None:
        watch_id = self._arm()
        job_id, _ = self.store.enqueue({
            "watch_id": watch_id, "kind": "build",
            "argv": [sys.executable, "-c", "import time; time.sleep(30)"],
            "cwd": str(self.repo.root), "resources": {"cpu_heavy": True},
        })
        worker = self.store.register_worker()
        job, attempt = self.store.claim(worker)
        with mock.patch("todo_orchestrator.background.runner.cpp_context_active", return_value=True):
            outcome = run_job(self.store, worker, job, attempt)
        self.store.finish(job_id, attempt, **outcome)
        self.store.stop_worker(worker)
        self.assertEqual(outcome["state"], "preempted")
        self.assertEqual(outcome["reason"], "foreground-context-compiler")
        with self.store.connect(readonly=True) as connection:
            row = connection.execute("SELECT state,retries_used,result_id FROM background_jobs WHERE id=?", (job_id,)).fetchone()
        self.assertEqual(dict(row), {"state": "queued", "retries_used": 0, "result_id": None})


if __name__ == "__main__":
    unittest.main()
