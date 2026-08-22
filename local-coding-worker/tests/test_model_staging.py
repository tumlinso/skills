from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "evals/model_staging.py"
SPEC = importlib.util.spec_from_file_location("model_staging", SCRIPT)
model_staging = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = model_staging
SPEC.loader.exec_module(model_staging)


class ModelStagingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cold = self.root / "cold"
        self.stage = self.root / "ssd-stage"
        self.candidate = self.cold / "candidate-a"
        self.candidate.mkdir(parents=True)
        payload = b"model-weights"
        (self.candidate / "model.gguf").write_bytes(payload)
        manifest = {
            "format": "CORE4-MODEL-ASSET/1",
            "schema_version": 1,
            "candidate_id": "candidate-a",
            "source": {"repository": "provider/model", "revision": "abc123"},
            "files": [{"path": "model.gguf", "bytes": len(payload),
                       "sha256": hashlib.sha256(payload).hexdigest()}],
        }
        (self.candidate / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.policy = model_staging.StoragePolicy.from_mapping({
            "canonical_root": str(self.cold),
            "staging_root": str(self.stage),
            "minimum_headroom_bytes": 1024,
        })

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_stages_verified_candidate_and_cleans_after_success(self) -> None:
        with mock.patch.object(model_staging, "_filesystem_type", return_value="ext4"):
            with model_staging.staged_candidate(self.policy, "candidate-a") as record:
                staged = Path(record["staged_dir"])
                self.assertEqual((staged / "model.gguf").read_bytes(), b"model-weights")
                self.assertEqual(record["source"]["revision"], "abc123")
            self.assertFalse(staged.exists())

    def test_checksum_failure_leaves_no_staged_candidate(self) -> None:
        (self.candidate / "model.gguf").write_bytes(b"model-weightx")
        with mock.patch.object(model_staging, "_filesystem_type", return_value="ext4"):
            with self.assertRaisesRegex(model_staging.StagingError, "checksum mismatch"):
                with model_staging.staged_candidate(self.policy, "candidate-a"):
                    pass
        self.assertFalse((self.stage / "candidate-a").exists())

    def test_interrupted_evaluation_cleans_staged_candidate(self) -> None:
        with mock.patch.object(model_staging, "_filesystem_type", return_value="ext4"):
            with self.assertRaises(KeyboardInterrupt):
                with model_staging.staged_candidate(self.policy, "candidate-a") as record:
                    staged = Path(record["staged_dir"])
                    raise KeyboardInterrupt
        self.assertFalse(staged.exists())

    def test_failed_child_command_cleans_staged_candidate(self) -> None:
        with mock.patch.object(model_staging, "_filesystem_type", return_value="ext4"):
            returncode = model_staging.run_staged(
                self.policy, "candidate-a", [sys.executable, "-c", "raise SystemExit(7)"],
            )
        self.assertEqual(returncode, 7)
        self.assertFalse((self.stage / "candidate-a").exists())

    def test_reports_exact_additional_ssd_headroom_required(self) -> None:
        usage = shutil._ntuple_diskusage(total=10_000, used=9_500, free=500)
        with mock.patch.object(model_staging, "_filesystem_type", return_value="ext4"), \
                mock.patch.object(model_staging.shutil, "disk_usage", return_value=usage):
            with self.assertRaises(model_staging.InsufficientStagingSpace) as caught:
                model_staging.verify_candidate(self.policy, "candidate-a")
        expected = len(b"model-weights") + 1024 - 500
        self.assertEqual(caught.exception.additional_bytes_required, expected)

    def test_rejects_ram_filesystem_as_primary_stage(self) -> None:
        with mock.patch.object(model_staging, "_filesystem_type", return_value="tmpfs"):
            with self.assertRaisesRegex(model_staging.StagingError, "RAM filesystem"):
                model_staging.verify_candidate(self.policy, "candidate-a")

    def test_rejects_path_traversal_and_overlapping_roots(self) -> None:
        with self.assertRaises(model_staging.StagingError):
            model_staging.verify_candidate(self.policy, "../escape")
        with self.assertRaises(model_staging.StagingError):
            model_staging.StoragePolicy.from_mapping({
                "canonical_root": str(self.cold),
                "staging_root": str(self.cold / "stage"),
                "minimum_headroom_bytes": 0,
            })


if __name__ == "__main__":
    unittest.main()
