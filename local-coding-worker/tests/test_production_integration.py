from __future__ import annotations

import sys
import os
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from local_worker.production_checks import _integrated_guards, _write_compact  # noqa: E402


class ProductionIntegrationGuardTests(unittest.TestCase):
    def fixture(self) -> dict:
        scenarios = [
            {"id": "source-trace", "mode": "readonly", "accepted": True,
             "child_execution_id": "read", "parent_task_completed": False},
            {"id": "diagnosis", "mode": "readonly", "accepted": True,
             "child_execution_id": "diag", "parent_task_completed": False},
            {"id": "needs-codex", "mode": "readonly", "accepted": True,
             "child_execution_id": "needs", "parent_task_completed": False},
            {"id": "cpp-fix", "mode": "writable", "accepted": True,
             "result_status": "accepted", "child_state": "accepted",
             "child_execution_id": "python", "parent_task_completed": False},
            {"id": "cuda-fix", "mode": "writable", "accepted": True,
             "result_status": "accepted", "child_state": "accepted", "cuda_auto_queue_state": "queued",
             "child_execution_id": "cuda", "parent_task_completed": False},
            {"id": "preemption-recovery", "mode": "recovery", "accepted": True},
        ]
        return {
            "scenarios": scenarios, "false_successes": 0, "scope_violations": 0,
            "codex_visible_result_bytes": 4096,
            "service": {"first_pid": 10, "second_pid": 10, "first_compatibility_key": "key",
                        "second_compatibility_key": "key", "second_reused": True,
                        "local_endpoint_bound": True, "explicit_model_bound": True},
            "preemption": {"evicted": True, "foreground_activated": True, "later_warm_succeeded": True},
            "cold_storage": {"payload_atime_ns_before": 1, "payload_atime_ns_after": 1,
                             "active_payload_in_ssd_cache": True},
        }

    def test_complete_integrated_evidence_passes_every_guard(self) -> None:
        self.assertTrue(all(_integrated_guards(self.fixture()).values()))

    def test_false_success_and_child_authority_mismatch_fail_closed(self) -> None:
        value = self.fixture()
        value["false_successes"] = 1
        value["scenarios"][3]["child_state"] = "ready_for_acceptance"
        guards = _integrated_guards(value)
        self.assertFalse(guards["zero_false_successes"])
        self.assertFalse(guards["writable_child_authority"])

    def test_compact_evidence_can_be_written_outside_the_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            previous = os.environ.get("CORE4_COMPACT_EVIDENCE_DIR")
            os.environ["CORE4_COMPACT_EVIDENCE_DIR"] = temporary
            try:
                result = _write_compact(Path("/unused"), "integrated-evaluation", {"ok": True})
            finally:
                if previous is None:
                    os.environ.pop("CORE4_COMPACT_EVIDENCE_DIR", None)
                else:
                    os.environ["CORE4_COMPACT_EVIDENCE_DIR"] = previous
            self.assertEqual(Path(result["evidence_path"]).parent, Path(temporary).resolve())
            self.assertTrue(Path(result["evidence_path"]).is_file())


if __name__ == "__main__":
    unittest.main()
