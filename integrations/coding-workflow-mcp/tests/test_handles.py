from __future__ import annotations

import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.handles import CapabilityStore, InvalidHandle


class CapabilityStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.state_dir = Path(self.temporary.name) / "state"
        self.repo = Path(self.temporary.name).resolve()
        self.store = CapabilityStore(self.state_dir)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_owner_only_permissions_and_opaque_entropy(self) -> None:
        handle = self.store.create_workflow({"repo": str(self.repo), "claim_token": "toc_secret"})
        self.assertTrue(handle.startswith("wf_"))
        self.assertGreaterEqual(len(handle.removeprefix("wf_")), 43)
        self.assertNotIn("secret", handle)
        self.assertEqual(self.store.permissions(), (0o700, 0o600))
        for suffix in ("-wal", "-shm"):
            candidate = Path(str(self.store.db_path) + suffix)
            if candidate.exists():
                self.assertEqual(candidate.stat().st_mode & 0o777, 0o600)

    def test_records_require_canonical_absolute_repo(self) -> None:
        with self.assertRaises(ValueError):
            self.store.create_workflow({"repo": "relative"})
        alias = self.store.create_delegation({"repo": str(self.repo), "execution_id": "worker-1"})
        self.assertEqual(self.store.get_delegation(alias)["execution_id"], "worker-1")

    def test_expiry_deletion_and_kind_validation(self) -> None:
        workflow = self.store.create_workflow({"repo": str(self.repo)}, ttl=0.01)
        delegation = self.store.create_delegation({"repo": str(self.repo)})
        with self.assertRaises(InvalidHandle):
            self.store.get_workflow(delegation)
        time.sleep(0.02)
        with self.assertRaises(InvalidHandle):
            self.store.get_workflow(workflow)
        self.store.delete(delegation)
        with self.assertRaises(InvalidHandle):
            self.store.get_delegation(delegation)

    def test_concurrent_process_style_instances(self) -> None:
        handles: list[str] = []
        errors: list[BaseException] = []
        barrier = threading.Barrier(8)

        def create(index: int) -> None:
            try:
                instance = CapabilityStore(self.state_dir)
                barrier.wait()
                handles.append(instance.create_workflow({"repo": str(self.repo), "index": index}))
            except BaseException as error:  # pragma: no cover - asserted below
                errors.append(error)

        threads = [threading.Thread(target=create, args=(index,)) for index in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(set(handles)), 8)
        self.assertEqual(sorted(self.store.get_workflow(item)["index"] for item in handles), list(range(8)))

    def test_terminal_delegation_is_collectable_then_sweepable(self) -> None:
        alias = self.store.create_delegation({"repo": str(self.repo), "status": "running"})
        self.store.update(alias, {"repo": str(self.repo), "status": "accepted"}, terminal=True)
        self.assertEqual(self.store.get_delegation(alias)["status"], "accepted")
        with closing(self.store._connect()) as connection:
            connection.execute("UPDATE capabilities SET expires_at=? WHERE handle=?", (time.time() - 1, alias))
        self.assertEqual(self.store.sweep(limit=1)["capabilities"], 1)

    def test_bounded_diagnostics_are_owner_only(self) -> None:
        diagnostic = self.store.write_diagnostic("x" * 20_000)
        self.assertTrue(diagnostic.startswith("diag_"))
        with closing(self.store._connect()) as connection:
            value = connection.execute(
                "SELECT message FROM diagnostics WHERE diagnostic_id=?", (diagnostic,)
            ).fetchone()[0]
        self.assertEqual(len(value), 16_384)


if __name__ == "__main__":
    unittest.main()
