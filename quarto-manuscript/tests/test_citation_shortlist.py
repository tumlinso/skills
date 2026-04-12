import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PAPER_FIXTURES = ROOT / "tests" / "paper_fixtures"
CITATION_FIXTURES = ROOT / "tests" / "citation_fixtures"
sys.path.insert(0, str(SCRIPTS))

from build_citation_shortlist import build_shortlist_text, claims_from_input
from common import build_bibtex_entry, read_json
from rank_paper_hits import load_claims, rank_hits
from search_arxiv import parse_arxiv_feed
from search_biorxiv import parse_biorxiv_payload
from search_pubmed import parse_pubmed_xml


class CitationShortlistTests(unittest.TestCase):
    def test_claims_from_input_uses_local_extractor_for_manuscript_paths(self) -> None:
        claims = claims_from_input(PAPER_FIXTURES / "citation_paper", max_claims=3)
        self.assertGreaterEqual(len(claims), 3)
        self.assertIn("Cardiac fibrosis is associated with high mortality.", {claim["sentence"] for claim in claims})

    def test_rank_hits_prefers_pubmed_for_background_and_arxiv_for_benchmark(self) -> None:
        claims = load_claims(CITATION_FIXTURES / "citation_gaps.json")
        hits = read_json(CITATION_FIXTURES / "paper_hits.json")["hits"]
        ranked = rank_hits(claims, hits, top_k=2)

        first_group = ranked["ranked_results"][0]
        second_group = ranked["ranked_results"][1]
        self.assertEqual(first_group["results"][0]["source"], "pubmed")
        self.assertIn("background", first_group["results"][0]["integration_note"].lower())
        self.assertEqual(second_group["results"][0]["source"], "arxiv")
        self.assertEqual(second_group["results"][0]["manuscript_role"], "benchmark comparison")

    def test_shortlist_text_and_bibtex_are_compact(self) -> None:
        claims = load_claims(CITATION_FIXTURES / "citation_gaps.json")
        hits = read_json(CITATION_FIXTURES / "paper_hits.json")["hits"]
        ranked = rank_hits(claims, hits, top_k=2)
        text = build_shortlist_text(ranked["ranked_results"], sources=["pubmed", "biorxiv", "arxiv"], input_mode="manuscript-linked")
        self.assertIn("Sources searched: pubmed, biorxiv, arxiv", text)
        self.assertIn("Cardiac fibrosis is associated with high mortality.", text)
        bibtex = build_bibtex_entry(ranked["ranked_results"][0]["results"][0], index=1)
        self.assertIn("@article{", bibtex)
        self.assertIn("10.1000/cardiac.2024.1", bibtex)

    def test_source_parsers_still_extract_expected_fields(self) -> None:
        xml_text = (CITATION_FIXTURES / "pubmed_efetch.xml").read_text(encoding="utf-8")
        pubmed_hits = parse_pubmed_xml(xml_text, "cardiac fibrosis is associated with high mortality", claim_id="claim-1")
        self.assertEqual(pubmed_hits[0]["doi"], "10.1000/cardiac.2024.1")
        self.assertEqual(pubmed_hits[0]["source"], "pubmed")

        feed_text = (CITATION_FIXTURES / "arxiv_feed.xml").read_text(encoding="utf-8")
        arxiv_hits = parse_arxiv_feed(feed_text, "single-cell atlas integration benchmark", claim_id="claim-2")
        self.assertEqual(arxiv_hits[0]["source_id"], "2404.12345")

        payload = json.loads((CITATION_FIXTURES / "biorxiv_details.json").read_text(encoding="utf-8"))
        biorxiv_hits = parse_biorxiv_payload(payload, "single-cell atlas integration benchmark", claim_id="claim-2")
        self.assertEqual(biorxiv_hits[0]["doi"], "10.1101/2024.04.01.123456")


if __name__ == "__main__":
    unittest.main()
