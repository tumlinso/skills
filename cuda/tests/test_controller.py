from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
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
from v2_helpers import V2Repo, base_plan, safe_task  # noqa: E402


class ControllerTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
