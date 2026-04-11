import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from build_citation_shortlist import build_shortlist_text
from common import build_bibtex_entry, read_json
from rank_paper_hits import load_claims, rank_hits


class ShortlistFlowTests(unittest.TestCase):
    def test_rank_hits_prefers_pubmed_for_background_and_arxiv_for_benchmark(self) -> None:
        claims = load_claims(FIXTURES / "citation_gaps.json")
        hits = read_json(FIXTURES / "paper_hits.json")["hits"]
        ranked = rank_hits(claims, hits, top_k=2)

        first_group = ranked["ranked_results"][0]
        second_group = ranked["ranked_results"][1]
        self.assertEqual(first_group["results"][0]["source"], "pubmed")
        self.assertIn("background", first_group["results"][0]["integration_note"].lower())
        self.assertEqual(second_group["results"][0]["source"], "arxiv")
        self.assertEqual(second_group["results"][0]["manuscript_role"], "benchmark comparison")

    def test_shortlist_text_and_bibtex_are_compact(self) -> None:
        claims = load_claims(FIXTURES / "citation_gaps.json")
        hits = read_json(FIXTURES / "paper_hits.json")["hits"]
        ranked = rank_hits(claims, hits, top_k=2)
        text = build_shortlist_text(ranked["ranked_results"], sources=["pubmed", "biorxiv", "arxiv"], input_mode="manuscript-linked")
        self.assertIn("Sources searched: pubmed, biorxiv, arxiv", text)
        self.assertIn("Cardiac fibrosis is associated with high mortality.", text)
        bibtex = build_bibtex_entry(ranked["ranked_results"][0]["results"][0], index=1)
        self.assertIn("@article{", bibtex)
        self.assertIn("10.1000/cardiac.2024.1", bibtex)


if __name__ == "__main__":
    unittest.main()
