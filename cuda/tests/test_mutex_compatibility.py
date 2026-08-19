from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path


MUTEX = Path(__file__).resolve().parents[1] / "scripts" / "with_benchmark_mutex.sh"


class MutexCompatibilityTests(unittest.TestCase):
    def test_direct_mode_retains_output_status_and_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "benchmark.lock"
            result = subprocess.run([str(MUTEX), "--lock-file", str(lock), "--label", "compat", "--", sys.executable, "-c", "raise SystemExit(7)"], text=True, capture_output=True)
            self.assertEqual(result.returncode, 7)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, f"[benchmark-mutex] acquired compat via {lock}\n[benchmark-mutex] released compat via {lock}\n")
            self.assertFalse(Path(str(lock) + ".foreground-intent").exists())

    def test_opt_in_background_relinquishes_for_foreground_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "benchmark.lock"
            marker = Path(str(lock) + ".foreground-intent")
            environment = os.environ.copy()
            environment.update(CUDA_BENCHMARK_COORDINATION_MODE="background", CUDA_BACKGROUND_GPU_UUIDS="GPU-test")
            process = subprocess.Popen([str(MUTEX), "--lock-file", str(lock), "--label", "background", "--", sys.executable, "-c", "import time; time.sleep(30)"], env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            deadline = time.monotonic() + 5
            while not Path(str(lock) + ".gpu.GPU-test.lock").exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            marker.write_text("foreground\n", encoding="utf-8")
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 75)
            self.assertEqual(stdout, "")
            self.assertIn("acquired background", stderr)


if __name__ == "__main__":
    unittest.main()
