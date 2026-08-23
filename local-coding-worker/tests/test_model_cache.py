from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock
import sys

SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))
from local_worker.model_cache import ModelCache, ModelCacheError


class ModelCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.cold = self.root / "cold"
        self.cache_root = self.root / "cache"
        self.cache = ModelCache(self.cache_root, self.cold)
        self.payload = b"GGUF" + b"model-weights" * 32
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.write_candidate("candidate-a", self.payload)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def write_candidate(self, candidate_id: str, payload: bytes) -> None:
        candidate = self.cold / candidate_id
        candidate.mkdir(parents=True)
        (candidate / "source.gguf").write_bytes(payload)
        manifest = {
            "format": "CORE4-MODEL-ASSET/1",
            "schema_version": 1,
            "candidate_id": candidate_id,
            "source": {"repository": "provider/model", "revision": "abc123"},
            "files": [{
                "path": "source.gguf",
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            }],
        }
        (candidate / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def test_atomic_install_quick_full_verify_and_activation(self) -> None:
        installed = self.cache.install("candidate-a")
        self.assertTrue(installed["installed"])
        self.assertEqual(installed["verification"], "quick")
        directory = self.cache.payload_dir("candidate-a", self.digest)
        self.assertEqual((directory / "model.gguf").read_bytes(), self.payload)
        self.assertTrue((directory / "READY").is_file())
        self.assertFalse(list(self.cache_root.glob(".partial-*")))
        self.assertEqual(self.cache.verify("candidate-a", self.digest, full=True)["verification"], "full")
        active = self.cache.activate("candidate-a", self.digest)
        self.assertEqual(active["payload_sha256"], self.digest)
        self.assertEqual(self.cache.inspect()["active"]["candidate_id"], "candidate-a")
        with self.assertRaisesRegex(ModelCacheError, "active"):
            self.cache.remove("candidate-a", self.digest)

    def test_metadata_change_promotes_quick_verify_to_full_hash(self) -> None:
        self.cache.install("candidate-a")
        model = self.cache.payload_dir("candidate-a", self.digest) / "model.gguf"
        model.touch()
        verified = self.cache.verify("candidate-a", self.digest, full=False)
        self.assertEqual(verified["verification"], "full")

    def test_corrupt_cold_payload_never_becomes_ready(self) -> None:
        (self.cold / "candidate-a/source.gguf").write_bytes(b"GGUF" + b"x" * (len(self.payload) - 4))
        with self.assertRaisesRegex(ModelCacheError, "checksum mismatch"):
            self.cache.install("candidate-a")
        self.assertFalse(self.cache.payload_dir("candidate-a", self.digest).exists())
        self.assertFalse(list(self.cache_root.glob(".partial-*")))

    def test_remove_refuses_live_lease(self) -> None:
        second = b"GGUF" + b"second" * 32
        digest = hashlib.sha256(second).hexdigest()
        self.write_candidate("candidate-b", second)
        self.cache.install("candidate-b")
        with self.cache.lease("candidate-b", digest, "service-1"):
            with self.assertRaisesRegex(ModelCacheError, "leased"):
                self.cache.remove("candidate-b", digest)
        self.assertTrue(self.cache.remove("candidate-b", digest)["removed"])

    def test_install_reports_exact_space_deficit_with_margin(self) -> None:
        usage = shutil._ntuple_diskusage(total=1000, used=999, free=1)
        with mock.patch("local_worker.model_cache.shutil.disk_usage", return_value=usage):
            with self.assertRaisesRegex(ModelCacheError, "additional_bytes_required"):
                self.cache.install("candidate-a")


if __name__ == "__main__":
    unittest.main()
