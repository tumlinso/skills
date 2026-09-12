"""Acceptance checks for the immutable WF2 Todo donor inventory."""
from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
INVENTORY = REPO / "docs/workflow_foundation_v2/baseline/todo_orchestrator_inventory.json"
FIXTURE = REPO / "docs/workflow_foundation_v2/baseline/disposable_fixture_v1.json"
RECOVERY = REPO / "docs/workflow_foundation_v2/baseline/RECOVERY.md"
CTXPP_HOST = REPO / "docs/workflow_foundation_v2/baseline/CTXPP_AND_HOST_CONTRACT.md"
BASELINE = "3652874793401944e3cde30a3134aeb5615316ba"


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True)


class TodoDonorInventoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(INVENTORY.read_text(encoding="utf-8"))

    def test_complete_git_inventory_has_stable_blob_identities(self) -> None:
        self.assertEqual(self.data["baseline_commit"], BASELINE)
        self.assertEqual(self.data["source_root"], "todo-orchestrator")
        rows = git("ls-tree", "-r", "--long", BASELINE, "--", "todo-orchestrator").splitlines()
        observed = []
        for row in rows:
            metadata, path = row.split("\t", 1)
            mode, kind, object_id, size = metadata.split()
            observed.append({"path": path, "mode": mode, "kind": kind,
                             "git_blob": object_id, "bytes": int(size)})
        self.assertEqual(self.data["tracked_files"], observed)
        self.assertEqual(self.data["tracked_file_count"], len(observed))
        self.assertEqual(self.data["subtree_git_object"], git("rev-parse", f"{BASELINE}:todo-orchestrator").strip())

    def test_consumer_audit_is_exact_and_records_unknown_consumer_risk(self) -> None:
        self.assertEqual(self.data["consumer_audit"]["roots"], ["cuda", "local-coding-worker", "cpp-context-compiler"])
        self.assertTrue(self.data["consumer_audit"]["exact_paths"])
        self.assertIn("unknown external consumers", self.data["consumer_audit"]["risk"].lower())
        for path in self.data["consumer_audit"]["exact_paths"]:
            self.assertTrue((REPO / path).is_file(), path)

    def test_inventory_excludes_live_todo_authority_data(self) -> None:
        encoded = INVENTORY.read_text(encoding="utf-8")
        self.assertNotIn(".todo-orchestrator/", encoded)
        self.assertNotIn("state.snapshot", encoded)
        self.assertNotIn("capability_handle", encoded)
        self.assertEqual(self.data["live_authority_exported"], False)

    def test_disposable_fixture_is_sanitized_and_source_is_recoverable(self) -> None:
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["format"], "wf2-disposable-todo-fixture-v1")
        self.assertFalse(fixture["provenance"]["live_authority_exported"])
        self.assertEqual(fixture["provenance"]["real_project_databases_touched"], [])
        self.assertFalse(fixture["redaction"]["contains_live_data"])
        encoded = json.dumps(fixture["project"], sort_keys=True).lower()
        for forbidden in fixture["redaction"]["forbidden_fields"]:
            self.assertNotIn('"' + forbidden + '"', encoded)
        self.assertNotIn("cellerator", encoded)
        self.assertNotIn("glasshelix", encoded)
        self.assertIn(BASELINE, RECOVERY.read_text(encoding="utf-8"))
        subprocess.check_call(["git", "cat-file", "-e", f"{BASELINE}^{{commit}}"], cwd=REPO)

    def test_ctxpp_and_host_contract_separates_capabilities_and_scope(self) -> None:
        contract = CTXPP_HOST.read_text(encoding="utf-8").lower()
        for phrase in ("standalone", "fallback", "read/query", "refresh and rewrite", "advisory", "nor represents an os- or cluster-wide reservation"):
            self.assertIn(phrase, contract)
        packet = (REPO / "cpp-context-compiler/scripts/ctxpp_packet.py").read_text(encoding="utf-8")
        self.assertIn("except (ImportError, OSError, RuntimeError, ValueError)", packet)
        self.assertIn("file_hashes", packet)
        host = (REPO / "todo-orchestrator/todo_orchestrator/background/host.py").read_text(encoding="utf-8")
        self.assertIn("Lazy host-global authority for physical resources", host)
        self.assertIn("ram_limit", host)


if __name__ == "__main__":
    unittest.main()
