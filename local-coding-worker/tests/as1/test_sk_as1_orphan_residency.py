"""CPU-only orphan recovery: native cache fixtures, mocked physical proofs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from local_worker.model_cache import ModelCache
from local_worker.supervisor import ProductionBackend, SupervisorError


class OrphanRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.cache = ModelCache(root / "cache", root / "cold", lease_root=root / "leases")
        payload = b"GGUF-orphan-test"
        self.digest = hashlib.sha256(payload).hexdigest()
        cold = self.cache.cold_root / "fixture"
        cold.mkdir(parents=True)
        (cold / "model.gguf").write_bytes(payload)
        (cold / "asset-manifest.json").write_text(json.dumps({
            "format": "CORE4-MODEL-ASSET/1", "candidate_id": "fixture",
            "files": [{"path": "model.gguf", "sha256": self.digest, "bytes": len(payload)}]}))
        self.cache.install("fixture")
        self.lease = self.cache.lease("fixture", self.digest, "owner-fixture")
        self.lease.__enter__()
        self.addCleanup(lambda: self.lease.__exit__(None, None, None))
        self.lease_path = self.cache.lease_root / "fixture" / self.digest / "owner-fixture.json"
        self.backend = ProductionBackend.__new__(ProductionBackend)
        self.backend.repo_root = root
        self.backend.service_state_root = root / "state"
        self.backend.profile = {"server": {"binary": "/fixture/server"},
            "deployment_policy": {"allowed_gpu_uuids": ["GPU-fixture"]}}
        self.backend.runtime = SimpleNamespace(host=Mock())
        self.backend.runtime.host.owner.return_value = None
        self.backend.cache = self.cache
        self.native_lease = patch.object(self.cache, "lease", wraps=self.cache.lease).start()
        self.backend._recovery_checked = False
        self.observation = {"available": True,
            "devices": [{"uuid": "GPU-fixture", "memory_used_mib": 12}], "processes": []}
        self.backend._observe_residency = Mock(side_effect=lambda uuids: dict(self.observation))
        self.marker = {"format": "CORE4-OWNED-RESIDENCY/1", "owner_id": "owner-fixture",
            "slot_id": "slot-fixture", "project_root": str(root),
            "service_state_root": str(self.backend.service_state_root),
            "source_sha256": "a" * 64, "gpu_uuids": ["GPU-fixture"],
            "memory_baseline": {"GPU-fixture": 0}, "resource_ids": ["accelerator:GPU-fixture"],
            "origin": {"pid": os.getpid(), "process_start": "fixture"},
            "process": {"pid": 2147483647, "process_group": 2147483647,
                        "process_start": "fixture", "boot_id": "fixture", "executable": "/fixture/server"}}
        self.path = self.backend._marker_path("slot-fixture")
        self.path.parent.mkdir(parents=True)
        self.write_marker()
        self.terminate = patch("local_worker.supervisor.terminate_owned").start()
        self.addCleanup(patch.stopall)

    def write_marker(self):
        self.path.write_text(json.dumps(self.marker))
        self.path.chmod(0o600)

    def refuse(self, *, lease_present=True):
        with self.assertRaisesRegex(SupervisorError, "recovery_blocked"):
            self.backend._recover_residencies()
        self.assertTrue(self.path.exists())
        self.assertEqual(self.lease_path.exists(), lease_present)
        self.terminate.assert_not_called()
        self.backend.runtime.host.release.assert_not_called()
        self.native_lease.assert_not_called()

    def test_absent_orphan_releases_native_lease_archives_and_is_idempotent(self):
        self.backend._recover_residencies()
        self.native_lease.assert_called_once_with("fixture", self.digest, "owner-fixture")
        self.assertFalse(self.path.exists())
        self.assertFalse(self.lease_path.exists())
        archived = json.loads((self.path.parent / "recovered-orphans" / self.path.name).read_text())
        self.assertEqual(archived["marker"], self.marker)
        self.assertEqual(archived["model_lease"]["payload_sha256"], self.digest)
        self.backend._recovery_checked = False
        self.backend._recover_residencies()
        self.terminate.assert_not_called()
        self.backend.runtime.host.release.assert_not_called()

    def test_live_pid_and_reused_pid_refuse_without_signals(self):
        self.marker["process"].update(pid=os.getpid(), process_group=os.getpid())
        self.write_marker()
        self.refuse()

    def released_owner(self):
        self.marker.update(generation="generation-fixture", residency_capability="b" * 64)
        self.write_marker()
        return {"id": self.marker["owner_id"], "state": "released",
            "residency_release_verified": 1, "residency_protected": 0,
            "owner_kind": "service", "service_id": "core4-local-fixture",
            "project_root": str(self.backend.repo_root), "pid": self.marker["process"]["pid"],
            "process_start": self.marker["process"]["process_start"], "resources": [],
            "residency_metadata_json": json.dumps({"phase": "spawned",
                "model_pid": self.marker["process"]["pid"],
                "process_start": self.marker["process"]["process_start"],
                "origin": self.marker["origin"], "baseline": self.marker["memory_baseline"],
                "resource_ids": sorted(self.marker["resource_ids"]),
                "generation": self.marker["generation"], "residency_capability_sha256":
                    hashlib.sha256(self.marker["residency_capability"].encode()).hexdigest()})}

    def test_exact_native_verified_released_owner_recovers_cache_only(self):
        self.backend.runtime.host.owner.return_value = self.released_owner()
        self.backend._recover_residencies()
        self.native_lease.assert_called_once_with("fixture", self.digest, "owner-fixture")
        self.assertFalse(self.path.exists())
        self.assertFalse(self.lease_path.exists())
        self.terminate.assert_not_called()
        self.backend.runtime.host.release.assert_not_called()

    def test_released_owner_unverified_or_mismatched_refuses(self):
        original = self.released_owner()
        for key, value in (("id", "foreign"), ("residency_release_verified", 0), ("residency_protected", 1),
                           ("pid", 123), ("process_start", "foreign"),
                           ("project_root", "/foreign"), ("resources", ["accelerator:GPU-fixture"]),
                           ("owner_kind", "background"), ("service_id", "foreign"),
                           ("state", "stale"), ("state", "failed"), ("state", "active")):
            with self.subTest(key=key, value=value):
                self.backend.runtime.host.owner.return_value = {**original, key: value}
                self.refuse()
        metadata = json.loads(original["residency_metadata_json"])
        for key, value in (("generation", "foreign"), ("origin", {}), ("baseline", {}),
                           ("resource_ids", []), ("residency_capability_sha256", "f" * 64),
                           ("phase", "reserved"), ("model_pid", 123), ("process_start", "foreign")):
            with self.subTest(metadata=key):
                self.backend.runtime.host.owner.return_value = {**original,
                    "residency_metadata_json": json.dumps({**metadata, key: value})}
                self.refuse()

    def test_native_accelerator_and_nvlink_reservation_recovers(self):
        uuids = ["GPU-fixture", "GPU-second"]
        self.backend.profile["deployment_policy"]["allowed_gpu_uuids"] = uuids
        self.marker.update(gpu_uuids=uuids, memory_baseline=dict.fromkeys(uuids, 0),
            resource_ids=[*(f"accelerator:{gpu}" for gpu in uuids),
                          "interference:nvlink:runtime:1-3"])
        self.backend.runtime.host.list.return_value = [
            {"id": f"accelerator:{gpu}", "tags": {"nvlink_domain": "runtime:1-3"}}
            for gpu in uuids]
        self.observation["devices"].append({"uuid": "GPU-second", "memory_used_mib": 12})
        self.write_marker()
        self.backend._recover_residencies()
        self.backend.runtime.host.list.assert_called_once_with(kind="accelerator")
        self.native_lease.assert_called_once_with("fixture", self.digest, "owner-fixture")
        self.assertFalse(self.path.exists())
        self.assertFalse(self.lease_path.exists())
        self.terminate.assert_not_called()
        self.backend.runtime.host.release.assert_not_called()
        self.backend.runtime.host.compound_gpu_bundles.assert_not_called()

    def test_unrelated_or_incomplete_interference_resources_refuse(self):
        self.backend.runtime.host.list.return_value = [
            {"id": "accelerator:GPU-fixture", "tags": {"nvlink_domain": "runtime:1-3"}}]
        for extra in (["interference:nvlink:foreign"], ["profiler:nvidia"],
                      ["interference:nvlink:runtime:1-3", "interference:pcie:foreign"],
                      ["accelerator:GPU-other"], ["accelerator:GPU-fixture"]):
            with self.subTest(extra=extra):
                self.marker["resource_ids"] = ["accelerator:GPU-fixture", *extra]
                self.write_marker()
                self.refuse()

    def test_interference_requires_registered_accelerator_identity(self):
        self.marker["resource_ids"].append("interference:nvlink:runtime:1-3")
        self.backend.runtime.host.list.return_value = []
        self.write_marker()
        self.refuse()

    def test_partial_native_domain_set_refuses(self):
        uuids = ["GPU-fixture", "GPU-second"]
        self.backend.profile["deployment_policy"]["allowed_gpu_uuids"] = uuids
        self.marker.update(gpu_uuids=uuids,
            resource_ids=[*(f"accelerator:{gpu}" for gpu in uuids),
                          "interference:nvlink:runtime:1-3"])
        self.backend.runtime.host.list.return_value = [
            {"id": "accelerator:GPU-fixture", "tags": {"nvlink_domain": "runtime:1-3"}},
            {"id": "accelerator:GPU-second", "tags": {"nvlink_domain": "runtime:0-2"}}]
        self.write_marker()
        self.refuse()

    def test_unknown_pid_presence_proof_refuses(self):
        original_stat = Path.stat
        def guarded_stat(path, *args, **kwargs):
            if str(path) == "/proc/2147483647":
                raise PermissionError("unknown PID presence")
            return original_stat(path, *args, **kwargs)
        with patch.object(Path, "stat", guarded_stat):
            self.refuse()

    def test_active_owner_historical_source_and_identity_mismatch_refuse(self):
        self.backend.runtime.host.owner.return_value = {"state": "active", "pid": 2147483647,
            "process_start": "fixture", "project_root": str(self.backend.repo_root),
            "resources": self.marker["resource_ids"]}
        self.refuse()
        import local_worker.supervisor as supervisor
        self.marker["source_sha256"] = hashlib.sha256(Path(supervisor.__file__).read_bytes()).hexdigest()
        self.backend.runtime.host.owner.return_value["pid"] = 123
        self.write_marker()
        self.refuse()

    def test_disallowed_gpu_and_absent_allowlist_refuse(self):
        self.backend.profile["deployment_policy"]["allowed_gpu_uuids"] = ["GPU-other"]
        self.refuse()
        self.backend.profile["deployment_policy"] = {}
        self.refuse()

    def test_missing_lease_and_mismatched_lease_proof_refuse(self):
        self.lease_path.unlink()
        with self.assertRaisesRegex(SupervisorError, "proof_unavailable"):
            self.backend._recover_residencies()
        self.assertTrue(self.path.exists())
        self.lease_path.write_text(json.dumps({"owner_id": "foreign", "payload_sha256": self.digest}))
        self.lease_path.chmod(0o600)
        self.refuse()

    def test_unavailable_stale_nonfinite_memory_and_gpu_processes_refuse(self):
        samples = [
            {"available": False},
            {**self.observation, "observed_unix": time.time() - 60},
            {**self.observation, "devices": [{"uuid": "GPU-fixture", "memory_used_mib": float("nan")}]},
            {**self.observation, "devices": [{"uuid": "GPU-fixture", "memory_used_mib": 17}]},
            {**self.observation, "processes": [{"uuid": "GPU-fixture", "pid": 2147483647}]},
            {**self.observation, "processes": [{"uuid": "GPU-fixture", "pid": 123}]},
            {**self.observation, "processes": None},
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                self.observation = sample
                self.refuse()

    def test_marker_identity_permissions_and_symlink_refuse(self):
        original = json.loads(json.dumps(self.marker))
        for key, value in (("format", "unknown"), ("project_root", "/foreign"),
                           ("service_state_root", "/foreign"), ("process", None),
                           ("source_sha256", "unknown"), ("slot_id", "../foreign")):
            with self.subTest(key=key):
                self.marker = {**original, key: value}
                self.write_marker()
                self.refuse()
        self.marker = original
        self.write_marker()
        self.path.chmod(0o644)
        self.refuse()
        self.path.chmod(0o600)
        target = self.path.with_suffix(".saved")
        self.path.rename(target)
        self.path.symlink_to(target)
        self.refuse()

    def test_cache_artifact_corruption_refuses(self):
        (self.cache.payload_dir("fixture", self.digest) / "model.gguf").write_bytes(b"broken")
        self.refuse()

    def test_ambiguous_or_symlink_lease_proof_refuses(self):
        other = self.cache.lease_root / "other" / self.digest / self.lease_path.name
        other.parent.mkdir(parents=True)
        other.write_bytes(self.lease_path.read_bytes())
        other.chmod(0o600)
        self.refuse()
        other.unlink()
        saved = self.lease_path.with_suffix(".saved")
        self.lease_path.rename(saved)
        self.lease_path.symlink_to(saved)
        self.refuse()

    def crash_after_lease_exit(self):
        original_unlink = Path.unlink
        def interrupted_unlink(path, *args, **kwargs):
            if path == self.path:
                raise OSError("simulated crash after native lease exit")
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, "unlink", interrupted_unlink):
            with self.assertRaisesRegex(SupervisorError, "simulated crash"):
                self.backend._recover_residencies()
        self.assertTrue(self.path.exists())
        self.assertFalse(self.lease_path.exists())
        self.native_lease.reset_mock()
        return self.path.parent / "recovered-orphans" / self.path.name

    def test_crash_after_lease_exit_resumes_without_recreating_lease(self):
        archive = self.crash_after_lease_exit()
        original_archive = archive.read_bytes()
        self.backend._observe_residency.reset_mock()
        self.backend._recover_residencies()
        self.backend._observe_residency.assert_called_once_with(["GPU-fixture"])
        self.native_lease.assert_not_called()
        self.terminate.assert_not_called()
        self.backend.runtime.host.release.assert_not_called()
        self.assertFalse(self.path.exists())
        self.assertFalse(self.lease_path.exists())
        self.assertEqual(archive.read_bytes(), original_archive)

    def test_crash_resume_repeats_quiescence_and_pid_absence(self):
        self.crash_after_lease_exit()
        self.observation["devices"][0]["memory_used_mib"] = 17
        self.refuse(lease_present=False)
        self.observation["devices"][0]["memory_used_mib"] = 12
        original_stat = Path.stat
        def present_pid(path, *args, **kwargs):
            if str(path) == "/proc/2147483647":
                return original_stat(Path("/proc") / str(os.getpid()))
            return original_stat(path, *args, **kwargs)
        with patch.object(Path, "stat", present_pid):
            self.refuse(lease_present=False)

    def test_changed_or_invalid_archive_refuses_even_with_recomputed_digest(self):
        archive = self.crash_after_lease_exit()
        original = json.loads(archive.read_text())
        mutations = [
            lambda record: record.update(format="unknown"),
            lambda record: record.update(phase="unrecognized"),
            lambda record: record["marker"].update(source_sha256="b" * 64),
            lambda record: record["model_lease"].update(owner_id="foreign"),
            lambda record: record["model_lease"].update(lease_root="/foreign"),
            lambda record: record["model_lease"].update(lease_path="/foreign"),
            lambda record: record.update(extra="ambiguous"),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                record = json.loads(json.dumps(original))
                record.pop("proof_sha256")
                mutate(record)
                record["proof_sha256"] = hashlib.sha256(json.dumps(
                    record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
                archive.write_text(json.dumps(record))
                self.refuse(lease_present=False)
        archive.write_text(json.dumps({**original, "proof_sha256": "0" * 64}))
        self.refuse(lease_present=False)
        archive.write_text("not JSON")
        self.refuse(lease_present=False)

    def test_crash_resume_rejects_unsafe_archive_and_foreign_present_lease(self):
        archive = self.crash_after_lease_exit()
        archive.chmod(0o644)
        self.refuse(lease_present=False)
        archive.chmod(0o600)
        saved = archive.with_suffix(".saved")
        archive.rename(saved)
        archive.symlink_to(saved)
        self.refuse(lease_present=False)
        archive.unlink()
        saved.rename(archive)
        other = self.cache.lease_root / "other" / self.digest / self.lease_path.name
        other.parent.mkdir(parents=True)
        other.write_text(json.dumps({"owner_id": "owner-fixture", "payload_sha256": self.digest}))
        other.chmod(0o600)
        self.refuse(lease_present=False)
        self.assertTrue(other.exists())


if __name__ == "__main__":
    unittest.main()
