from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

CUDA_ROOT = Path(__file__).resolve().parents[1]
TODO_ROOT = CUDA_ROOT.parent / "todo-orchestrator"
for value in (CUDA_ROOT / "scripts", TODO_ROOT, TODO_ROOT / "tests"):
    if str(value) not in sys.path:
        sys.path.insert(0, str(value))

import cuda_controller as controller  # noqa: E402
from todo_orchestrator.background.store import BackgroundStore  # noqa: E402
from todo_orchestrator.background.host import HostCoordinator  # noqa: E402
from v2_helpers import V2Repo, base_plan, safe_task  # noqa: E402


class ControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.host_runtime = tempfile.TemporaryDirectory()
        self.host_environment = mock.patch.dict(os.environ, {
            "TODO_BACKGROUND_HOST_RUNTIME_DIR": self.host_runtime.name,
            "CUDA_V100_BENCHMARK_MUTEX_PATH": str(Path(self.host_runtime.name) / "benchmark.lock"),
            "CUDA_BENCHMARK_FOREGROUND_INTENT_PATH": str(Path(self.host_runtime.name) / "benchmark.intent"),
        })
        self.host_environment.start()

    def tearDown(self) -> None:
        self.host_environment.stop()
        self.host_runtime.cleanup()

    def test_background_mutex_child_cannot_inherit_lock(self) -> None:
        lock = Path(os.environ["CUDA_V100_BENCHMARK_MUTEX_PATH"])
        probe = (
            "import os,sys; target=os.path.realpath(os.environ['CUDA_V100_BENCHMARK_MUTEX_PATH']); "
            "links=[]; "
            "[(links.append(os.path.realpath('/proc/self/fd/'+fd)) if os.path.exists('/proc/self/fd/'+fd) else None) "
            "for fd in os.listdir('/proc/self/fd')]; sys.exit(target in links)"
        )
        environment = {**os.environ, "CUDA_BENCHMARK_COORDINATION_MODE": "background"}
        completed = subprocess.run(
            [str(controller.MUTEX), "--", sys.executable, "-c", probe],
            env=environment, text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(subprocess.run(
            ["flock", "-n", str(lock), "-c", "true"], check=False,
        ).returncode, 0)

    def test_background_mutex_releases_after_abrupt_wrapper_death(self) -> None:
        lock = Path(os.environ["CUDA_V100_BENCHMARK_MUTEX_PATH"])
        pid_file = lock.with_suffix(".child")
        child = (
            "import os,time; from pathlib import Path; "
            f"Path({str(pid_file)!r}).write_text(str(os.getpid())); time.sleep(60)"
        )
        environment = {**os.environ, "CUDA_BENCHMARK_COORDINATION_MODE": "background"}
        wrapper = subprocess.Popen(
            [str(controller.MUTEX), "--", sys.executable, "-c", child],
            env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        child_pid = None
        try:
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not pid_file.exists():
                time.sleep(0.02)
            self.assertTrue(pid_file.exists())
            child_pid = int(pid_file.read_text())
            wrapper.kill()
            wrapper.wait(timeout=5)
            lock_deadline = time.monotonic() + 1
            available = False
            while time.monotonic() < lock_deadline:
                available = subprocess.run(
                    ["flock", "-n", str(lock), "-c", "true"], check=False,
                ).returncode == 0
                if available:
                    break
                time.sleep(0.02)
            self.assertTrue(available)
        finally:
            if wrapper.poll() is None:
                wrapper.kill()
                wrapper.wait(timeout=5)
            if child_pid is not None:
                try:
                    os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_arm_is_explicit_and_persistent(self) -> None:
        repo = V2Repo()
        try:
            (repo.root / "src").mkdir()
            (repo.root / "src/a.cu").write_text("__global__ void a() {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo.root), "add", "src/a.cu"], check=True)
            subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
            spec = {
                "schema_version": 1, "project_root": str(repo.root),
                "watch": {"paths": ["src/*.cu"]},
                "benchmark": {"argv": [sys.executable, "-c", "print('{\"latency\":1.0}')"],
                              "correctness_argv": [sys.executable, "-c", "pass"],
                              "metric": "latency", "direction": "minimize"},
                "policy": {"initial_characterization": False},
            }
            with mock.patch.object(controller, "probe_gpus", return_value=[]), mock.patch.object(controller, "wake_worker") as wake:
                result = controller.arm_background(spec)
            self.assertEqual(result["state"], "armed")
            self.assertEqual(BackgroundStore(repo.root).watch(result["watch_id"])["spec"]["benchmark"]["metric"], "latency")
            wake.assert_called_once()
        finally:
            repo.close()

    def test_relevant_completion_queues_one_immutable_benchmark_and_next_start_does_not_duplicate(self) -> None:
        repo = V2Repo()
        try:
            (repo.root / "src").mkdir()
            (repo.root / "src/a.cu").write_text("__global__ void a() {}\n", encoding="utf-8")
            (repo.root / "src/b.cu").write_text("__global__ void b() {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo.root), "add", "src"], check=True)
            subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
            repo.apply(base_plan([safe_task("CUDA-A", "src/a.cu"), safe_task("CUDA-B", "src/b.cu")]))
            spec = {
                "schema_version": 1, "project_root": str(repo.root), "watch": {"task_prefixes": ["CUDA-"]},
                "benchmark": {"argv": [sys.executable, "-c", "print('{\"latency\":1.0}')"],
                              "correctness_argv": [sys.executable, "-c", "pass"], "metric": "latency", "direction": "minimize"},
                "policy": {"initial_characterization": False, "benchmark_completed_steps": True},
            }
            with mock.patch.object(controller, "probe_gpus", return_value=[]), mock.patch.object(controller, "wake_worker"), mock.patch("todo_orchestrator.background.wake.wake_worker"):
                armed = controller.arm_background(spec)
                claim = repo.service.continue_work(task_id="CUDA-A")
                (repo.root / "src/a.cu").write_text("__global__ void a() { int x = 1; }\n", encoding="utf-8")
                subprocess.run(["git", "-C", str(repo.root), "add", "src/a.cu"], check=True)
                subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "step-a"], check=True)
                repo.service.complete(claim["claim"]["claim_token"], "implemented")
                first = controller.sync_watch(repo.root, armed["watch_id"])
                repo.service.continue_work(task_id="CUDA-B")
                second = controller.sync_watch(repo.root, armed["watch_id"])
            store = BackgroundStore(repo.root)
            with store.connect(readonly=True) as connection:
                benchmarks = connection.execute("SELECT task_id,todo_revision,snapshot_json FROM background_jobs WHERE kind='benchmark'").fetchall()
            self.assertEqual(first["queued"], 2)
            self.assertEqual(second["queued"], 0)
            self.assertEqual(len(benchmarks), 1)
            snapshot = json.loads(benchmarks[0]["snapshot_json"])
            self.assertEqual(benchmarks[0]["task_id"], "CUDA-A")
            self.assertTrue(Path(snapshot["source_root"]).is_dir())
            self.assertEqual(snapshot["commit"], subprocess.check_output(["git", "-C", str(repo.root), "rev-parse", "HEAD"], text=True).strip())
        finally:
            repo.close()

    def test_symbol_watch_matches_existing_todo_task_text(self) -> None:
        repo = V2Repo()
        try:
            repo.apply(base_plan([safe_task("CUDA-A", "src/a.cu", objective="Optimize fused_attention_kernel")]))
            with sqlite3.connect(repo.service.paths.db_file) as connection:
                self.assertTrue(controller.relevant_task(connection, "CUDA-A", {"symbols": ["fused_attention_kernel"]}))
                self.assertFalse(controller.relevant_task(connection, "CUDA-A", {"symbols": ["unrelated_kernel"]}))
        finally:
            repo.close()

    def test_background_crash_is_compact_and_healthy_results_stay_silent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".todo-orchestrator").mkdir()
            store = BackgroundStore(root)
            _, bad = store.record_external_result(kind="background-correctness", argv=["fake"], cwd=str(root), source_fingerprint="x", snapshot={},
                result={"status": "failed", "valid": False, "classification": "correctness-failure", "severity": 100,
                        "summary": "REVISION: crash, likely illegal access; skipped."}, artifacts=[])
            _, good = store.record_external_result(kind="background-benchmark", argv=["fake"], cwd=str(root), source_fingerprint="y", snapshot={},
                result={"status": "succeeded", "valid": True, "classification": "healthy", "severity": 0}, artifacts=[])
            visible = controller.evidence(root, "missing", "")
            self.assertEqual(len(visible["findings"]), 1)
            self.assertEqual(visible["findings"][0]["id"], bad)
            self.assertNotEqual(visible["findings"][0]["id"], good)
            self.assertEqual(set(visible["findings"][0]), {"id", "classification", "severity", "line"})
            self.assertNotIn("record", visible["findings"][0]["line"])

    def test_background_failure_uses_only_the_cheap_classifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "snapshot"
            source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "project_root": str(root), "watch": {},
                "benchmark": {
                    "argv": [sys.executable, "-c", "print('{\"latency\":1.0}')"],
                    "correctness_argv": [sys.executable, "-c", "import sys; sys.stderr.write('illegal memory access\\n'); sys.exit(1)"],
                    "metric": "latency", "direction": "minimize",
                },
            })
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "failure", "commit": "deadbeef"}
            with mock.patch.object(controller, "probe_gpus", return_value=[]):
                result = controller.background_stage(root, watch_id, "correctness", snapshot)
            self.assertEqual(result["classification"], "correctness-failure")
            self.assertEqual(result["failure_classifier"]["crash_class"], "device-memory-fault")
            self.assertEqual(result["summary"], "deadbeef: crash, likely device memory fault.")
            self.assertFalse(any("sanitizer" in str(item) or "cuda-gdb" in str(item) for item in result["record"]["argv"]))

    def test_cpp_context_slice_uses_public_api_and_fallback_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".ctxpp.toml").write_text("[project]\n", encoding="utf-8")
            request = {"context": {"target": "kernel", "intent": "performance", "budget": 900}}
            completed = subprocess.CompletedProcess([], 0, '{"format":"CTXPP-SLICE/1","files":[]}', "")
            with mock.patch.object(controller, "text_run", return_value=completed) as invoked:
                result = controller._ctxpp_context(request, root)
            self.assertEqual(result["provider"], "cpp-context-compiler")
            self.assertIn("slice", invoked.call_args.args[0])
            self.assertFalse((root / ".ctxpp").exists())

    def test_model_supplied_candidate_queues_build_correctness_and_benchmark(self) -> None:
        repo = V2Repo()
        try:
            snapshot_root = repo.root / "snapshot"
            snapshot_root.mkdir()
            snapshot = {"safe": True, "source_root": str(snapshot_root), "fingerprint": "abc", "commit": "deadbeef"}
            spec = {
                "project_root": str(repo.root), "watch": {},
                "benchmark": {"argv": ["base"], "correctness_argv": ["check"], "metric": "latency", "direction": "minimize"},
                "policy": {"initial_characterization": False},
                "candidates": [{"id": "tile-64", "build_argv": ["build", "64"], "argv": ["bench", "64"], "env": {"TILE": "64"}}],
            }
            store = BackgroundStore(repo.root)
            watch_id = store.arm_watch(spec)
            watch = store.watch(watch_id)
            jobs = controller.queue_revision(store, watch, snapshot, task_id="A", revision=1)
            with store.connect(readonly=True) as connection:
                kinds = [row[0] for row in connection.execute("SELECT kind FROM background_jobs ORDER BY created_at")]
            self.assertEqual(len(jobs), 5)
            self.assertEqual(kinds, ["correctness", "benchmark", "candidate-build", "candidate-correctness", "candidate-benchmark"])
        finally:
            repo.close()

    def test_legacy_build_and_test_releases_gpu_during_build(self) -> None:
        repo = V2Repo()
        try:
            source = repo.root / "snapshot"
            source.mkdir()
            spec = {
                "project_root": str(repo.root), "watch": {},
                "benchmark": {
                    "argv": ["bench"],
                    "correctness_argv": ["ctest", "--build-and-test", "{snapshot}", "build",
                                         "--build-target", "bench", "--test-command", "bench", "--check"],
                    "metric": "latency", "direction": "minimize", "gpus": 1,
                },
                "policy": {"initial_characterization": False, "max_background_gpus": 1},
            }
            store = BackgroundStore(repo.root)
            watch_id = store.arm_watch(spec)
            watch = store.watch(watch_id)
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "split", "commit": "deadbeef"}
            jobs = controller.queue_revision(store, watch, snapshot, task_id="A", revision=1)
            with store.connect(readonly=True) as connection:
                rows = connection.execute(
                    "SELECT id,kind,priority,resource_json FROM background_jobs ORDER BY created_at"
                ).fetchall()
                correctness_parent = connection.execute(
                    "SELECT depends_on_job_id FROM background_dependencies WHERE job_id=?", (rows[1]["id"],)
                ).fetchone()[0]
            self.assertEqual(len(jobs), 3)
            self.assertEqual([row["kind"] for row in rows], ["build", "correctness", "benchmark"])
            self.assertEqual(json.loads(rows[0]["resource_json"])["count"], 0)
            self.assertTrue(json.loads(rows[0]["resource_json"])["cpu_heavy"])
            self.assertGreater(json.loads(rows[0]["resource_json"])["cpu_threads"], 0)
            self.assertEqual(json.loads(rows[1]["resource_json"])["count"], 1)
            self.assertEqual(correctness_parent, rows[0]["id"])
            self.assertEqual(rows[2]["priority"], 25)
            self.assertEqual(json.loads(rows[2]["resource_json"])["exclusive_resources"], ["benchmark:cuda"])
            build, correctness = controller._base_stage_commands(spec["benchmark"])
            self.assertEqual(build[-1], "/usr/bin/true")
            self.assertEqual(correctness, ["bench", "--check"])
        finally:
            repo.close()

    def test_correctness_repeats_and_stops_at_first_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "snapshot"
            source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "project_root": str(root), "watch": {},
                "benchmark": {
                    "argv": ["bench"], "correctness_argv": ["check"],
                    "correctness_repetitions": 5, "metric": "latency", "direction": "minimize",
                },
            })
            records = [
                {"returncode": 0, "stdout": str(source / "out0"), "stderr": str(source / "err0")},
                {"returncode": 1, "stdout": str(source / "out1"), "stderr": str(source / "err1")},
            ]
            for name in ("out0", "err0", "out1", "err1"):
                (source / name).write_text("", encoding="utf-8")
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "repeat", "commit": "deadbeef"}
            with mock.patch.object(controller, "_capture", side_effect=records) as capture, \
                    mock.patch.object(controller, "probe_gpus", return_value=[]), \
                    mock.patch.object(controller, "_cheap_failure_classification", return_value={}):
                result = controller.background_stage(root, watch_id, "correctness", snapshot)
            self.assertFalse(result["valid"])
            self.assertEqual(len(result["records"]), 2)
            self.assertEqual(capture.call_count, 2)

    def test_backfill_queues_historical_immutable_revisions_once(self) -> None:
        repo = V2Repo()
        try:
            (repo.root / "kernel.cu").write_text("__global__ void old_kernel() {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo.root), "add", "kernel.cu"], check=True)
            subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "old"], check=True)
            old = subprocess.check_output(["git", "-C", str(repo.root), "rev-parse", "HEAD"], text=True).strip()
            (repo.root / "kernel.cu").write_text("__global__ void new_kernel() {}\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo.root), "add", "kernel.cu"], check=True)
            subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "new"], check=True)
            new = subprocess.check_output(["git", "-C", str(repo.root), "rev-parse", "HEAD"], text=True).strip()
            watch_spec = {
                "schema_version": 1, "project_root": str(repo.root), "watch": {"paths": ["kernel.cu"]},
                "benchmark": {"argv": ["bench"], "correctness_argv": ["check"], "metric": "latency", "direction": "minimize"},
                "policy": {"initial_characterization": False},
            }
            with mock.patch.object(controller, "probe_gpus", return_value=[]), mock.patch.object(controller, "wake_worker"):
                armed = controller.arm_background(watch_spec)
                request = {
                    "schema_version": 1, "project_root": str(repo.root), "watch_id": armed["watch_id"],
                    "mappings": [
                        {"task_id": "OLD", "source_revision": old, "todo_revision": 10,
                         "benchmark": {"argv": ["bench", "--old"]}},
                        {"task_id": "NEW", "source_revision": new, "todo_revision": 20},
                    ],
                }
                first = controller.enqueue_supplied_revisions(request, backfill=True)
                second = controller.enqueue_supplied_revisions(request, backfill=True)
            self.assertEqual(first["jobs_queued"], 4)
            self.assertEqual(second["jobs_queued"], 0)
            with BackgroundStore(repo.root).connect(readonly=True) as connection:
                rows = connection.execute("SELECT task_id,todo_revision,snapshot_json FROM background_jobs WHERE kind='benchmark' ORDER BY todo_revision").fetchall()
            self.assertEqual([(row["task_id"], row["todo_revision"]) for row in rows], [("OLD", 10), ("NEW", 20)])
            snapshots = [json.loads(row["snapshot_json"]) for row in rows]
            self.assertIn("old_kernel", (Path(snapshots[0]["source_root"]) / "kernel.cu").read_text(encoding="utf-8"))
            self.assertIn("new_kernel", (Path(snapshots[1]["source_root"]) / "kernel.cu").read_text(encoding="utf-8"))
            self.assertEqual(snapshots[0]["_benchmark_override"]["argv"], ["bench", "--old"])
        finally:
            repo.close()

    def test_initial_characterization_chains_nsys_before_ncu_and_focuses_two_kernels(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "snapshot"
            source.mkdir()
            store = BackgroundStore(root)
            watch_id = store.arm_watch({
                "project_root": str(root), "watch": {},
                "benchmark": {"argv": ["bench"], "correctness_argv": ["check"], "metric": "latency", "direction": "minimize"},
                "policy": {"initial_characterization": True},
            })
            watch = store.watch(watch_id)
            snapshot = {"safe": True, "source_root": str(source), "fingerprint": "profile", "commit": "deadbeef"}
            controller.queue_revision(store, watch, snapshot, task_id="A", revision=1, initial=True)
            with store.connect(readonly=True) as connection:
                nsys = connection.execute("SELECT id FROM background_jobs WHERE kind='nsys'").fetchone()[0]
                ncu = connection.execute("SELECT id FROM background_jobs WHERE kind='ncu'").fetchone()[0]
                dependency = connection.execute("SELECT depends_on_job_id FROM background_dependencies WHERE job_id=?", (ncu,)).fetchone()[0]
            self.assertEqual(dependency, nsys)
            cached = {"summary": {"summary": {"top_kernels": [{"name": "kernel<int>"}, {"name": "kernel2"}, {"name": "kernel3"}]}}}
            fake_store = mock.Mock()
            fake_store.latest_valid_result.return_value = cached
            kernel_filter = controller._focused_ncu_kernel_filter(fake_store, "watch", "profile")
            self.assertIn("kernel<int>", kernel_filter)
            self.assertIn("kernel2", kernel_filter)
            self.assertNotIn("kernel3", kernel_filter)

    def test_private_runtime_is_not_source_or_dirty_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
            (root / "source.txt").write_text("stable\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "source.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
            store = BackgroundStore(root)
            store.set_meta("private", {"value": 1})
            snapshot = controller.create_snapshot(root, store.paths.artifacts, [], allow_dirty=True)
            self.assertTrue(snapshot["safe"])
            self.assertFalse(snapshot["dirty"])
            self.assertEqual(snapshot["untracked"], [])
            self.assertFalse((Path(snapshot["source_root"]) / ".todo-orchestrator" / "runtime").exists())

    def test_foreground_run_preempts_another_projects_host_reservation(self) -> None:
        repo = V2Repo()
        try:
            (repo.root / "benchmark.txt").write_text("fixture\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo.root), "add", "benchmark.txt"], check=True)
            subprocess.run(["git", "-C", str(repo.root), "-c", "user.name=test", "-c", "user.email=test@example.invalid", "commit", "-qm", "base"], check=True)
            device = {"index": 0, "uuid": "GPU-cross-project", "name": "fake", "compute_capability": "7.0",
                      "memory_total_mib": 16000, "pci_bus_id": "0000:01:00.0", "driver_version": "test"}
            fact = {"id": "accelerator:GPU-cross-project", "kind": "accelerator", "tags": {"architecture": "volta"}}
            host = HostCoordinator()
            host.upsert_resources([fact])
            background = host.reserve_background(
                project_root=repo.root / "other", job_id="background", attempt_id="one",
                request={"ids": [fact["id"]]}, pid=os.getpid(),
            )
            released = threading.Event()

            def release_on_preempt():
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline and not host.preempt_requested(background[0]):
                    time.sleep(0.01)
                if host.preempt_requested(background[0]):
                    host.release(background[0])
                    released.set()

            thread = threading.Thread(target=release_on_preempt)
            thread.start()
            spec = {
                "project_root": str(repo.root), "recipe": "baseline",
                "argv": [sys.executable, "-c", "print('{\"latency\":1.0}')"],
                "metric": "latency", "warmups": 0, "repetitions": 1,
                "resources": {"gpu_uuids": ["GPU-cross-project"], "cpu_threads": 1},
            }
            idle = {"idle": True, "busy": False, "foreign_processes": False, "samples": []}
            with mock.patch.object(controller, "probe_gpus", return_value=[device]), \
                 mock.patch.object(controller, "resource_facts", return_value=[fact]), \
                 mock.patch.object(controller, "sample_devices", return_value=idle):
                result = controller.foreground_run(spec)
            thread.join(timeout=5)
            self.assertTrue(released.is_set())
            self.assertTrue(result["ok"], result)
        finally:
            repo.close()


if __name__ == "__main__":
    unittest.main()
