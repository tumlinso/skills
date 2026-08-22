from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from todo_orchestrator.background.host import HostCoordinator
from todo_orchestrator.background.store import BackgroundStore
from todo_orchestrator.runtime import (
    ContractError,
    RuntimeFacade,
    capture_source_identity,
    normalize_artifact_ref,
    normalize_command_spec,
    normalize_evidence_summary,
    normalize_resource_request,
    normalize_source_identity,
)


class RuntimeContractTests(unittest.TestCase):
    def test_schema_documents_and_dependency_free_normalizers(self) -> None:
        names = [
            "command-spec-v1.schema.json",
            "source-identity-v1.schema.json",
            "resource-request-v1.schema.json",
            "artifact-ref-v1.schema.json",
            "evidence-summary-v1.schema.json",
        ]
        documents = {name: json.loads((WORKSPACE / "contracts" / name).read_text(encoding="utf-8")) for name in names}
        self.assertTrue(all(item["$schema"].endswith("2020-12/schema") for item in documents.values()))
        self.assertTrue(all(item["additionalProperties"] is False for item in documents.values()))

        command = normalize_command_spec({"schema_version": 1, "argv": ["python", "-V"], "cwd": "."})
        self.assertEqual(command["env"], {})
        self.assertEqual(command["timeout_seconds"], 3600.0)
        with self.assertRaises(ContractError):
            normalize_command_spec("python -V")
        with self.assertRaises(ContractError):
            normalize_command_spec({"schema_version": 1, "argv": ["true"], "cwd": ".", "shell": True})

        request = normalize_resource_request({"schema_version": 1, "ids": ["accelerator:GPU-a"], "cpu_threads": 2})
        self.assertEqual(request["ids"], ["accelerator:GPU-a"])
        with self.assertRaises(ContractError):
            normalize_resource_request({"schema_version": 1, "ids": ["accelerator:GPU-a"], "count": 1})

        identity = normalize_source_identity({
            "schema_version": 1,
            "repo_root": "/tmp/repo",
            "git_head": "a" * 40,
            "dirty_paths": ["z.cpp", "a.cpp"],
            "fingerprint": "b" * 64,
        })
        self.assertEqual(identity["dirty_paths"], ["a.cpp", "z.cpp"])
        artifact = normalize_artifact_ref({
            "schema_version": 1, "kind": "report", "path": "out.json", "content_hash": None, "complete": True,
        })
        evidence = normalize_evidence_summary({
            "schema_version": 1,
            "status": "needs_codex",
            "valid": True,
            "contaminated": False,
            "severity": 1,
            "summary": {"reason": "architectural decision"},
            "artifacts": [artifact],
            "source_identity": identity,
        })
        self.assertEqual(evidence["status"], "needs_codex")

    def test_source_identity_is_content_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "runtime@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Runtime Test"], cwd=root, check=True)
            source = root / "source.cpp"
            source.write_text("int value = 1;\n", encoding="utf-8")
            subprocess.run(["git", "add", "source.cpp"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "baseline"], cwd=root, check=True)
            clean = capture_source_identity(root)
            self.assertEqual(clean["dirty_paths"], [])
            source.write_text("int value = 2;\n", encoding="utf-8")
            dirty = capture_source_identity(root)
            self.assertEqual(dirty["dirty_paths"], ["source.cpp"])
            self.assertNotEqual(clean["fingerprint"], dirty["fingerprint"])


class RuntimeFacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.host_runtime = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {"TODO_BACKGROUND_HOST_RUNTIME_DIR": self.host_runtime.name})
        self.environment.start()
        self.root = Path(self.temporary.name)
        self.store = BackgroundStore(self.root)
        self.host = HostCoordinator()
        self.facade = RuntimeFacade(self.root, store=self.store, host=self.host)
        self.identity = {
            "schema_version": 1,
            "repo_root": str(self.root),
            "git_head": None,
            "dirty_paths": [],
            "fingerprint": "0" * 64,
        }
        self.command = {"schema_version": 1, "argv": ["true"], "cwd": str(self.root), "timeout_seconds": 5}

    def tearDown(self) -> None:
        self.environment.stop()
        self.host_runtime.cleanup()
        self.temporary.cleanup()

    def test_jobs_artifacts_and_external_evidence_use_stable_contracts(self) -> None:
        first = self.facade.jobs.enqueue(kind="contract-test", command=self.command, source_identity=self.identity)
        duplicate = self.facade.jobs.enqueue(kind="contract-test", command=self.command, source_identity=self.identity)
        self.assertTrue(first["created"])
        self.assertFalse(duplicate["created"])
        self.assertEqual(first["job_id"], duplicate["job_id"])
        artifact_id = self.facade.artifacts.record(
            job_id=str(first["job_id"]),
            artifact={"schema_version": 1, "kind": "log", "path": "log.txt", "content_hash": None, "complete": True},
        )
        self.assertTrue(artifact_id)

        recorded = self.facade.jobs.record_external(
            kind="external-contract-test",
            command=self.command,
            source_identity=self.identity,
            evidence={
                "schema_version": 1,
                "status": "succeeded",
                "valid": True,
                "contaminated": False,
                "severity": 0,
                "summary": {"message": "bounded"},
                "artifacts": [
                    {"schema_version": 1, "kind": "report", "path": "report.json", "content_hash": None, "complete": True}
                ],
            },
        )
        result = self.facade.jobs.result(recorded["result_id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["source_identity"]["fingerprint"], "0" * 64)
        self.assertEqual(result["summary"], {"message": "bounded"})
        self.assertEqual(result["artifacts"][0]["kind"], "report")

    def test_host_facade_wraps_existing_atomic_coordinator(self) -> None:
        self.facade.host.upsert([
            {"id": "accelerator:GPU-a", "kind": "accelerator", "tags": {"island": "one"}},
            {"id": "accelerator:GPU-b", "kind": "accelerator", "tags": {"island": "two"}},
        ])
        self.assertEqual([item["id"] for item in self.facade.host.list(kind="accelerator")],
                         ["accelerator:GPU-a", "accelerator:GPU-b"])
        request = {"schema_version": 1, "ids": ["accelerator:GPU-a"]}
        reservation = self.facade.host.reserve_background(
            project_root=self.root, job_id="job-a", attempt_id="attempt-a", resource_request=request,
        )
        self.assertIsNotNone(reservation)
        blocked = self.facade.host.reserve_background(
            project_root=self.root / "other", job_id="job-b", attempt_id="attempt-b", resource_request=request,
        )
        self.assertIsNone(blocked)
        self.facade.host.release(str(reservation["owner_id"]))
        available = self.facade.host.reserve_background(
            project_root=self.root / "other", job_id="job-b", attempt_id="attempt-b", resource_request=request,
        )
        self.assertIsNotNone(available)
        self.facade.host.release(str(available["owner_id"]))


if __name__ == "__main__":
    unittest.main()
