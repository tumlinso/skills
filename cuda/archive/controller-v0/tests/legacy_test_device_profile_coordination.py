from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

CUDA_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = CUDA_ROOT / "scripts"
MUTEX = SCRIPTS / "with_benchmark_mutex.sh"
TODO_ROOT = CUDA_ROOT.parent / "todo-orchestrator"
for item in (SCRIPTS, TODO_ROOT):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

import cuda_controller as controller  # noqa: E402


class DeviceProfileCoordinationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.lock = self.root / "measurement.lock"
        self.marker = Path(str(self.lock) + ".foreground-intent")
        self.records = Path(str(self.marker) + ".owners")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def env(self, *, scope: str = "device", uuids: str = "GPU-A", background: bool = False) -> dict[str, str]:
        result = os.environ.copy()
        for key in (
            "CUDA_BENCHMARK_COORDINATION_MODE", "CUDA_BENCHMARK_LOCK_SCOPE",
            "CUDA_BENCHMARK_GPU_UUIDS", "CUDA_BACKGROUND_GPU_UUIDS",
            "CUDA_BENCHMARK_FOREGROUND_INTENT_HELD",
        ):
            result.pop(key, None)
        result.update({
            "CUDA_V100_BENCHMARK_MUTEX_PATH": str(self.lock),
            "CUDA_BENCHMARK_FOREGROUND_INTENT_PATH": str(self.marker),
            "CUDA_BENCHMARK_FOREGROUND_INTENT_RECORDS_DIR": str(self.records),
            "CUDA_BENCHMARK_LOCK_SCOPE": scope,
            "CUDA_BENCHMARK_GPU_UUIDS": uuids,
        })
        if background:
            result["CUDA_BENCHMARK_COORDINATION_MODE"] = "background"
            result["CUDA_BACKGROUND_GPU_UUIDS"] = uuids
        else:
            result["CUDA_BENCHMARK_FOREGROUND_INTENT_HELD"] = "1"
        return result

    def launch(self, label: str, env: dict[str, str], script: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            [str(MUTEX), "--label", label, "--", sys.executable, "-c", script],
            env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )

    def test_device_captures_on_distinct_uuids_overlap(self) -> None:
        barrier = self.root / "barrier"
        barrier.mkdir()
        code = (
            "import pathlib,time,sys\n"
            f"p=pathlib.Path({str(barrier)!r})\n"
            "(p/('ready-'+str(sys.argv[1]))).write_text('ready')\n"
            "deadline=time.monotonic()+3\n"
            "while time.monotonic()<deadline and len(list(p.glob('ready-*')))<2:\n time.sleep(.01)\n"
            "(p/('start-'+sys.argv[1])).write_text(str(time.monotonic()))\n"
            "time.sleep(.2)\n"
            "(p/('end-'+sys.argv[1])).write_text(str(time.monotonic()))\n"
        )
        first = self.launch("profile-a", self.env(uuids="GPU-A"), code.replace("sys.argv[1]", "'a'"))
        second = self.launch("profile-b", self.env(uuids="GPU-B"), code.replace("sys.argv[1]", "'b'"))
        for process in (first, second):
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
        intervals = []
        for label in ("a", "b"):
            intervals.append((float((barrier / f"start-{label}").read_text()),
                              float((barrier / f"end-{label}").read_text())))
        self.assertLess(max(interval[0] for interval in intervals), min(interval[1] for interval in intervals))

    def test_same_uuid_captures_serialize(self) -> None:
        first_stamp = self.root / "first.json"
        second_stamp = self.root / "second.json"
        first_started = self.root / "first.started"
        first_code = (
            "import json,pathlib,time; "
            f"p=pathlib.Path({str(first_stamp)!r}); a=time.monotonic(); pathlib.Path({str(first_started)!r}).touch(); time.sleep(.25); "
            "p.write_text(json.dumps({'start':a,'end':time.monotonic()}))"
        )
        second_code = (
            "import json,pathlib,time; "
            f"p=pathlib.Path({str(second_stamp)!r}); a=time.monotonic(); "
            "p.write_text(json.dumps({'start':a}))"
        )
        first = self.launch("profile-first", self.env(uuids="GPU-A"), first_code)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not first_started.exists():
            time.sleep(.01)
        self.assertTrue(first_started.exists())
        second = self.launch("profile-second", self.env(uuids="GPU-A"), second_code)
        for process in (first, second):
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
        first_result = json.loads(first_stamp.read_text())
        second_result = json.loads(second_stamp.read_text())
        self.assertGreaterEqual(second_result["start"], first_result["end"])

    def test_timed_benchmark_takes_exclusive_gate_against_device_profile(self) -> None:
        profile = self.root / "profile.json"
        bench = self.root / "benchmark.json"
        profile_started = self.root / "profile.started"
        profile_code = (
            "import json,pathlib,time; a=time.monotonic(); "
            f"pathlib.Path({str(profile_started)!r}).touch(); time.sleep(.25); "
            f"pathlib.Path({str(profile)!r}).write_text(json.dumps({{'end':time.monotonic()}}))"
        )
        bench_code = (
            "import json,pathlib,time; "
            f"pathlib.Path({str(bench)!r}).write_text(json.dumps({{'start':time.monotonic()}}))"
        )
        profile_job = self.launch("profile", self.env(uuids="GPU-A"), profile_code)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not profile_started.exists():
            time.sleep(.01)
        self.assertTrue(profile_started.exists())
        benchmark_env = self.env(scope="host", uuids="")
        benchmark_job = self.launch("benchmark", benchmark_env, bench_code)
        for process in (profile_job, benchmark_job):
            _, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stderr)
        self.assertGreaterEqual(json.loads(bench.read_text())["start"], json.loads(profile.read_text())["end"])

    def test_pending_host_measurement_yields_new_profiles_but_running_profile_finishes(self) -> None:
        profile_started = self.root / "running-profile.started"
        profile_finished = self.root / "running-profile.finished"
        host_started = self.root / "host-benchmark.started"
        profile_code = (
            "import pathlib,time; "
            f"pathlib.Path({str(profile_started)!r}).touch(); time.sleep(.3); "
            f"pathlib.Path({str(profile_finished)!r}).touch()"
        )
        host_code = f"import pathlib; pathlib.Path({str(host_started)!r}).touch()"

        running_profile = self.launch("running-profile", self.env(uuids="GPU-A"), profile_code)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not profile_started.exists():
            time.sleep(.01)
        self.assertTrue(profile_started.exists())

        records, host_intent = controller._intent_paths(self.marker, "queued-debug", "host", ["GPU-C"])
        host_environment = self.env(scope="host", uuids="")
        debug_argv, _ = controller._recipe({"recipe": "compute-sanitizer", "argv": ["unused"]}, self.root)
        separator = debug_argv.index("--")
        self.assertEqual(debug_argv[0], str(MUTEX))
        self.assertEqual(debug_argv[separator + 1], str(SCRIPTS / "debug_compute_sanitizer.sh"))
        simulated_debug_argv = [*debug_argv[:separator + 1], sys.executable, "-c", host_code]
        host_debug = subprocess.Popen(simulated_debug_argv, env=host_environment, text=True,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.marker.exists():
            time.sleep(.01)
        self.assertTrue(self.marker.exists())

        new_profile = self.launch("new-profile", self.env(uuids="GPU-B"), "pass")
        _, new_profile_stderr = new_profile.communicate(timeout=3)
        self.assertEqual(new_profile.returncode, 75, new_profile_stderr)

        _, running_stderr = running_profile.communicate(timeout=3)
        _, debug_stderr = host_debug.communicate(timeout=3)
        self.assertEqual(running_profile.returncode, 0, running_stderr)
        self.assertEqual(host_debug.returncode, 0, debug_stderr)
        self.assertTrue(profile_finished.exists())
        self.assertTrue(host_started.exists())
        controller._clear_intent_paths(self.marker, "queued-debug", records, host_intent)
        self.assertFalse(self.marker.exists())

    def test_controller_debug_recipes_enter_host_mutex_scope(self) -> None:
        for recipe, script in (("compute-sanitizer", "debug_compute_sanitizer.sh"),
                               ("cuda-gdb", "debug_cuda_gdb.sh")):
            with self.subTest(recipe=recipe):
                argv, _ = controller._recipe({"recipe": recipe, "argv": ["unused"]}, self.root)
                separator = argv.index("--")
                self.assertEqual(argv[0], str(MUTEX))
                self.assertEqual(argv[separator + 1], str(SCRIPTS / script))

    def test_opposite_multigpu_orders_do_not_deadlock(self) -> None:
        code = "import time; time.sleep(.08)"
        left = self.launch("left", self.env(uuids="GPU-B,GPU-A"), code)
        right = self.launch("right", self.env(uuids="GPU-A,GPU-B"), code)
        for process in (left, right):
            _, stderr = process.communicate(timeout=3)
            self.assertEqual(process.returncode, 0, stderr)

    def test_foreground_owner_records_do_not_clear_each_other(self) -> None:
        records, first = controller._intent_paths(self.marker, "owner-a", "host", ["GPU-A"])
        _, second = controller._intent_paths(self.marker, "owner-b", "host", ["GPU-B"])
        self.assertTrue(self.marker.exists())
        self.assertEqual(len(list(records.glob("*.host"))), 2)
        controller._clear_intent_paths(self.marker, "owner-a", records, first)
        self.assertTrue(self.marker.exists())
        self.assertEqual(len(list(records.glob("*.host"))), 1)
        controller._clear_intent_paths(self.marker, "owner-b", records, second)
        self.assertFalse(self.marker.exists())

    def test_device_intents_are_uuid_scoped_and_owner_specific(self) -> None:
        records, first = controller._intent_paths(self.marker, "owner-a", "device", ["GPU-A"])
        _, second = controller._intent_paths(self.marker, "owner-b", "device", ["GPU-B"])
        self.assertFalse(self.marker.exists())
        self.assertEqual(len(list(records.glob("*.device.GPU-*"))), 2)
        controller._clear_intent_paths(self.marker, "owner-a", records, first)
        self.assertEqual(len(list(records.glob("*.device.GPU-*"))), 1)
        controller._clear_intent_paths(self.marker, "owner-b", records, second)
        self.assertEqual(list(records.iterdir()), [])

    def test_invalid_uuid_does_not_create_an_intent_record(self) -> None:
        with self.assertRaises(ValueError):
            controller._intent_paths(self.marker, "owner-a", "device", ["../../GPU-A"])
        self.assertFalse(self.records.exists())

    def test_device_scope_without_uuid_falls_back_to_host_marker(self) -> None:
        environment = self.env(scope="device", uuids="")
        environment.pop("CUDA_BENCHMARK_FOREGROUND_INTENT_HELD", None)
        code = f"import pathlib; assert pathlib.Path({str(self.marker)!r}).exists()"
        process = self.launch("conservative-fallback", environment, code)
        _, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 0, stderr)
        self.assertFalse(self.marker.exists())

    def test_legacy_singleton_intent_still_blocks_device_background_work(self) -> None:
        self.marker.write_text("legacy-owner\n", encoding="utf-8")
        process = self.launch("legacy-yield", self.env(uuids="GPU-B", background=True), "pass")
        _, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 75, stderr)

    def test_device_background_obeys_matching_intent_and_host_timing_yields_globally(self) -> None:
        records, intent = controller._intent_paths(self.marker, "foreground-a", "device", ["GPU-A"])
        allowed = self.launch("other-device", self.env(uuids="GPU-B", background=True), "pass")
        _, stderr = allowed.communicate(timeout=3)
        self.assertEqual(allowed.returncode, 0, stderr)
        blocked = self.launch("same-device", self.env(uuids="GPU-A", background=True),
                              "pass")
        _, stderr = blocked.communicate(timeout=3)
        self.assertEqual(blocked.returncode, 75, stderr)
        benchmark = self.launch("timed-benchmark", self.env(scope="host", uuids="GPU-B", background=True),
                                "pass")
        _, stderr = benchmark.communicate(timeout=3)
        self.assertEqual(benchmark.returncode, 75, stderr)
        controller._clear_intent_paths(self.marker, "foreground-a", records, intent)

    def test_foreground_cancellation_kills_descendants_and_releases_locks(self) -> None:
        pid_file = self.root / "pids.json"
        code = (
            "import json,pathlib,subprocess,sys,time; "
            "child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); "
            f"pathlib.Path({str(pid_file)!r}).write_text(json.dumps([__import__('os').getpid(),child.pid])); "
            "time.sleep(60)"
        )
        process = self.launch("cancel-profile", self.env(uuids="GPU-A"), code)
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not pid_file.exists():
            time.sleep(.01)
        self.assertTrue(pid_file.exists())
        pids = json.loads(pid_file.read_text())
        process.send_signal(signal.SIGTERM)
        _, stderr = process.communicate(timeout=3)
        self.assertEqual(process.returncode, 143, stderr)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline and any(self._running(pid) for pid in pids):
            time.sleep(.02)
        self.assertFalse(any(self._running(pid) for pid in pids))
        self.assertEqual(subprocess.run(["flock", "-n", str(self.lock), "-c", "true"], check=False).returncode, 0)
        gpu_lock = self.lock.with_name(self.lock.name + ".gpu.GPU-A.lock")
        self.assertEqual(subprocess.run(["flock", "-n", str(gpu_lock), "-c", "true"], check=False).returncode, 0)

    @staticmethod
    def _running(pid: int) -> bool:
        try:
            state = Path(f"/proc/{pid}/stat").read_text().split()[2]
        except (FileNotFoundError, ProcessLookupError):
            return False
        return state != "Z"

    def test_background_ncu_drops_host_global_resource_claims(self) -> None:
        request = controller._resource_request({"benchmark": {"gpus": 1}}, "ncu")
        self.assertEqual(request["exclusive_resources"], [])
        system_profile = controller._resource_request({"benchmark": {"gpus": 1}}, "nsys")
        self.assertIn("profiler:nvidia", system_profile["exclusive_resources"])
        self.assertIn("benchmark:cuda", system_profile["exclusive_resources"])

    def test_controller_reasserts_scope_and_admitted_identity_after_task_environment(self) -> None:
        expected_lock = str(self.root / "controller.lock")
        expected_marker = expected_lock + ".intent"
        environment = {
            "CUDA_V100_BENCHMARK_MUTEX_PATH": "/candidate/lock",
            "CUDA_BENCHMARK_FOREGROUND_INTENT_PATH": "/candidate/intent",
            "CUDA_BENCHMARK_LOCK_SCOPE": "device",
            "CUDA_BENCHMARK_GPU_UUIDS": "GPU-UNADMITTED",
            "CUDA_BENCHMARK_COORDINATION_MODE": "foreground",
            "CUDA_VISIBLE_DEVICES": "7",
        }
        with patch.dict(os.environ, {
            "CUDA_V100_BENCHMARK_MUTEX_PATH": expected_lock,
            "CUDA_BENCHMARK_FOREGROUND_INTENT_PATH": expected_marker,
        }, clear=False):
            controller._apply_execution_coordination(environment, [2], ["GPU-ADMITTED"],
                                                     background=True, recipe="benchmark")
        self.assertEqual(environment["CUDA_V100_BENCHMARK_MUTEX_PATH"], expected_lock)
        self.assertEqual(environment["CUDA_BENCHMARK_FOREGROUND_INTENT_PATH"], expected_marker)
        self.assertEqual(environment["CUDA_BENCHMARK_LOCK_SCOPE"], "host")
        self.assertEqual(environment["CUDA_BENCHMARK_GPU_UUIDS"], "GPU-ADMITTED")
        self.assertEqual(environment["CUDA_BENCHMARK_COORDINATION_MODE"], "background")
        self.assertEqual(environment["CUDA_VISIBLE_DEVICES"], "2")
        controller._apply_execution_coordination(environment, [2], ["GPU-ADMITTED"],
                                                 background=False, recipe="ncu")
        self.assertEqual(environment["CUDA_BENCHMARK_LOCK_SCOPE"], "device")
        self.assertEqual(environment["CUDA_BENCHMARK_COORDINATION_MODE"], "foreground")
        self.assertEqual(environment["CUDA_BENCHMARK_FOREGROUND_INTENT_HELD"], "1")
        controller._apply_execution_coordination(environment, [], [], background=False, recipe="build")
        self.assertEqual(environment["CUDA_BENCHMARK_LOCK_SCOPE"], "host")
        self.assertNotIn("CUDA_VISIBLE_DEVICES", environment)


if __name__ == "__main__":
    unittest.main()
