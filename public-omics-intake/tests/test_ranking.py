from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

from rank_candidates import load_weights, rank_records


class RankingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.query_spec = json.loads((FIXTURE_DIR / "rank_query_spec.json").read_text())
        self.records = json.loads((FIXTURE_DIR / "rank_candidates.json").read_text())
        self.weights = load_weights(SCRIPTS_DIR / "default_ranking_weights.json")

    def test_ranking_is_deterministic(self) -> None:
        first = rank_records(self.records, self.query_spec, self.weights)
        second = rank_records(self.records, self.query_spec, self.weights)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["primary_accession"], "GSE171555")
        self.assertGreater(first[0]["integratability_score"], first[1]["integratability_score"])

    def test_incomplete_metadata_is_penalized(self) -> None:
        ranked = rank_records(self.records, self.query_spec, self.weights)
        geo = next(item for item in ranked if item["primary_accession"] == "GSE171555")
        sra = next(item for item in ranked if item["primary_accession"] == "PRJNA720779")
        self.assertGreater(
            geo["ranking_breakdown"]["metadata_richness"]["score"],
            sra["ranking_breakdown"]["metadata_richness"]["score"],
        )


if __name__ == "__main__":
    unittest.main()
