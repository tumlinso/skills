from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from common import EASY, POOR, RESTRUCTURE, classify_candidate, summarize_candidates


class CandidateClassificationTests(unittest.TestCase):
    def test_regular_reduction_loop_is_easy(self) -> None:
        summary = classify_candidate(
            {
                "id": "axpy",
                "location": "solver.cpp:44",
                "compute_dense": True,
                "stable_data_region": True,
                "reduction": True,
                "collapse_depth": 2,
            }
        )
        self.assertEqual(summary["classification"], EASY)
        self.assertIn("parallel loop", summary["suggested_directives"])
        self.assertIn("reduction", summary["suggested_directives"])
        self.assertIn("collapse(2)", summary["suggested_directives"])

    def test_scan_and_indirect_indexing_need_restructuring(self) -> None:
        summary = classify_candidate(
            {
                "id": "prefix-gather",
                "location": "graph.c:91",
                "scan": True,
                "indirect_indexing": True,
                "stable_data_region": True,
                "branchiness": "medium",
            }
        )
        self.assertEqual(summary["classification"], RESTRUCTURE)
        self.assertIn("scan or prefix dependency", summary["blockers"])
        self.assertIn("indirect indexing", summary["blockers"])

    def test_pointer_heavy_loop_is_poor_target(self) -> None:
        summary = classify_candidate(
            {
                "id": "linked-update",
                "location": "mesh.cpp:120",
                "pointer_heavy": True,
                "pointer_chasing": True,
            }
        )
        self.assertEqual(summary["classification"], POOR)
        self.assertEqual(summary["suggested_directives"], [])

    def test_tiny_transfer_dominated_loop_is_poor_target(self) -> None:
        summary = classify_candidate(
            {
                "id": "small-postprocess",
                "location": "post.f90:12",
                "tiny_loop": True,
                "transfer_dominated": True,
            }
        )
        self.assertEqual(summary["classification"], POOR)
        self.assertIn("transfer-dominated region", summary["blockers"])

    def test_summary_collects_shared_blockers(self) -> None:
        summary = summarize_candidates(
            [
                {"id": "a", "location": "a.c:1", "aliasing_risk": True},
                {"id": "b", "location": "b.c:2", "allocation_churn": True},
            ]
        )
        self.assertEqual(summary["counts"][RESTRUCTURE], 2)
        self.assertIn("aliasing risk", summary["shared_blockers"])
        self.assertIn("allocation churn", summary["shared_blockers"])


if __name__ == "__main__":
    unittest.main()
