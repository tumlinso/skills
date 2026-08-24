from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL))

from local_worker.policy import DelegationPolicy, PolicyError
from local_worker.reviewer import review_plan
from local_worker.telemetry import FORMAT, build_policy_report


def negative_bakeoff() -> dict:
    return {
        "format": "CORE4-HOST-BAKEOFF/1",
        "status": "completed",
        "selection": None,
        "summary": {"evaluated_candidates": 8, "phase_a_survivors": 4, "phase_b_survivors": 0},
        "phases": {"B": [
            {"candidate_id": "small", "status": "completed", "acceptance_rate": 1 / 3,
             "tasks": [{"accepted": True, "frontier_rework_required": 0},
                       {"accepted": False, "frontier_rework_required": 1},
                       {"accepted": False, "frontier_rework_required": 1}]},
            {"candidate_id": "wide", "status": "completed", "acceptance_rate": 2 / 3,
             "tasks": [{"accepted": True, "frontier_rework_required": 0},
                       {"accepted": False, "frontier_rework_required": 1},
                       {"accepted": True, "frontier_rework_required": 0}]},
        ]},
    }


class PolicyTests(unittest.TestCase):
    def test_negative_bakeoff_keeps_real_delegation_and_extra_calls_disabled(self) -> None:
        policy = DelegationPolicy.from_bakeoff(negative_bakeoff())
        self.assertFalse(policy.real_local_enabled)
        self.assertFalse(policy.reviewer_enabled)
        self.assertFalse(policy.double_solve_enabled)
        self.assertEqual(policy.hot_idle_seconds, 0)
        self.assertEqual(policy.max_real_workers, 0)
        self.assertTrue(policy.needs_codex_is_success)

    def test_fake_backend_compatibility_and_ctxpp_budget_tiers_are_preserved(self) -> None:
        policy = DelegationPolicy.from_bakeoff(negative_bakeoff())
        self.assertTrue(policy.decision("explain", backend="fake")["eligible"])
        self.assertFalse(policy.decision("explain", backend="real")["eligible"])
        self.assertEqual(policy.decision("explain")["packet_budget_tokens"], 1200)
        self.assertEqual(policy.decision("review")["packet_budget_tokens"], 2500)
        self.assertEqual(policy.decision("test_plan")["packet_budget_tokens"], 2500)
        self.assertEqual(policy.decision("debug")["packet_budget_tokens"], 10000)
        with self.assertRaises(PolicyError):
            policy.decision("architect")

    def test_reviewer_guard_preserves_needs_codex_without_another_model_call(self) -> None:
        policy = DelegationPolicy.from_bakeoff(negative_bakeoff())
        plan = review_plan(policy, role="review", primary_outcome="needs_codex",
                           request_reviewer=True, request_double_solve=True)
        self.assertEqual(plan["outcome"], "NEEDS_CODEX")
        self.assertTrue(plan["successful_handoff"])
        self.assertEqual(plan["mode"], "single")
        self.assertEqual(plan["additional_local_calls"], 0)

    def test_report_records_measured_negative_result_without_inventing_defaults(self) -> None:
        report = build_policy_report(negative_bakeoff(), source_sha256="a" * 64)
        self.assertEqual(report["format"], FORMAT)
        self.assertEqual(report["measurement"]["accepted_task_attempts"], 3)
        self.assertEqual(report["measurement"]["frontier_rework_events"], 3)
        self.assertEqual(report["measurement"]["nearest_candidate"]["candidate_id"], "wide")
        self.assertIsNone(report["deployment"]["selected_candidate"])
        self.assertIsNone(report["context"]["model_context_default"])

    def test_checked_in_integrated_evidence_replaces_stale_policy_report(self) -> None:
        self.assertFalse((SKILL / "evals/results/policy-report.json").exists())
        path = SKILL / "evals/results/compact/integrated-evaluation.json"
        report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(report["format"], "CORE4-INTEGRATED-EVALUATION/1")
        self.assertTrue(report["ok"])
        self.assertEqual(report["false_successes"], 0)
        self.assertEqual(report["scope_violations"], 0)
        encoded = json.dumps(report).casefold()
        for secret_marker in ("toc_", "toch_", "api_key", "password"):
            self.assertNotIn(secret_marker, encoded)


if __name__ == "__main__":
    unittest.main()
