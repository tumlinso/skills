from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/inspect_host.py"
SPEC = importlib.util.spec_from_file_location("inspect_host", SCRIPT)
inspect_host = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(inspect_host)


class HostManifestTests(unittest.TestCase):
    def test_gpu_csv_derives_volta_architecture_without_fixed_bundles(self) -> None:
        rows = inspect_host.parse_gpu_csv(
            "2, Tesla V100-SXM2-16GB, GPU-two, 16384, 16000, 7.0, 580.173.02\n"
            "7, Tesla V100-SXM2-16GB, GPU-seven, 16384, 15900, 7.0, 580.173.02\n"
        )
        self.assertEqual([row["index"] for row in rows], [2, 7])
        self.assertEqual({row["architecture"] for row in rows}, {"sm_70"})

    def test_meminfo_is_reported_in_bytes(self) -> None:
        self.assertEqual(
            inspect_host.parse_meminfo("MemTotal:       1024 kB\nMemAvailable:    512 kB\n"),
            {"total_bytes": 1048576, "available_bytes": 524288},
        )

    def test_cache_scan_lists_only_model_weight_formats(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "model.gguf").write_bytes(b"1234")
            (root / "notes.txt").write_text("not a weight", encoding="utf-8")
            record = inspect_host._scan_cache(root)
        self.assertEqual(record["weight_file_count"], 1)
        self.assertEqual(record["weight_bytes_listed"], 4)
        self.assertTrue(record["weight_files"][0]["path"].endswith("model.gguf"))

    def test_manifest_is_read_only_and_discovers_topology_at_runtime(self) -> None:
        def fake_run(argv, timeout=10.0):
            if "--query-gpu=index,name,uuid,memory.total,memory.free,compute_cap,driver_version" in argv:
                output = "0, Tesla V100, GPU-a, 16384, 16000, 7.0, 580.1"
            elif argv[-2:] == ["topo", "-m"]:
                output = "GPU0\\tX"
            elif argv[-1] == "--version" and "nvcc" in argv[0]:
                output = "Cuda compilation tools, release 12.9, V12.9.86"
            else:
                output = "version 1"
            return {"argv": argv, "returncode": 0, "stdout": output, "stderr": ""}

        available = {"nvidia-smi", "nvcc", "llama-server", "codex"}
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(inspect_host, "_run", side_effect=fake_run), \
                mock.patch.object(inspect_host, "_which", side_effect=lambda name: f"/bin/{name}" if name in available else None):
            manifest = inspect_host.inspect_host([Path(temporary) / "absent"])
        self.assertEqual(manifest["format"], "CORE4-HOST-MANIFEST/1")
        self.assertTrue(manifest["inspection_only"])
        self.assertFalse(manifest["topology"]["hard_coded_bundles"])
        self.assertTrue(manifest["cuda"]["explicit_cuda_12x_available"])
        self.assertFalse(manifest["adapters"]["qwen_code"]["available"])
        self.assertFalse(manifest["usable_model_weights_present"])


if __name__ == "__main__":
    unittest.main()
