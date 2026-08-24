from __future__ import annotations

import sys
import os
import importlib.util
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from local_worker.production_checks import _dual_release_guards, _integrated_guards, _write_compact  # noqa: E402


def _cli_module():
    scripts = SKILL_ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("core4_local_worker_cli", scripts / "local_worker.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        if str(scripts) in sys.path:
            sys.path.remove(str(scripts))


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

    def test_dual_release_guards_require_promoted_profile_and_real_evidence(self) -> None:
        profile = {"deployment_policy": {"max_real_workers": 2, "initial_warm_workers": 1,
                                          "worker_layout": "one-per-runtime-discovered-island"}}
        evidence = {"ok": True, "guards": {"dual_worker_capacity": 2,
            "single_worker_fallback": True, "two_disjoint_islands_proven": True,
            "two_concurrent_delegations_proven": True, "hot_reuse_without_reload": True,
            "third_worker_oversubscription_blocked": True, "selective_preemption": True,
            "global_preemption": True, "memory_guard_passed": True}}
        self.assertTrue(all(_dual_release_guards(profile, evidence).values()))
        evidence["guards"]["selective_preemption"] = False
        self.assertFalse(_dual_release_guards(profile, evidence)["dual_worker_release_evidence"])

    def test_nonblocking_launch_hides_claim_token_from_process_argv(self) -> None:
        module = _cli_module()
        with tempfile.TemporaryDirectory() as temporary, \
                mock.patch.object(module, "runtime_root", return_value=Path(temporary)), \
                mock.patch.object(module.subprocess, "Popen") as popen:
            popen.return_value.pid = 123
            result = module._launch_delegate(Path.cwd(), "toc_secret", "readonly", None)
            argv = popen.call_args.args[0]
            self.assertNotIn("toc_secret", argv)
            self.assertEqual(result["state"], "running")
            request = json.loads(next((Path(temporary) / "delegations").glob("*.request.json")).read_text())
            self.assertEqual(request["claim_token"], "toc_secret")
            self.assertEqual(oct((Path(temporary) / "delegations").stat().st_mode & 0o777), "0o700")


if __name__ == "__main__":
    unittest.main()
