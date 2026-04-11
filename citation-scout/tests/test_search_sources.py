import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from search_arxiv import parse_arxiv_feed
from search_biorxiv import parse_biorxiv_payload
from search_pubmed import parse_pubmed_xml


class SearchParsingTests(unittest.TestCase):
    def test_parse_pubmed_xml_extracts_abstract_and_doi(self) -> None:
        xml_text = (FIXTURES / "pubmed_efetch.xml").read_text(encoding="utf-8")
        hits = parse_pubmed_xml(xml_text, "cardiac fibrosis is associated with high mortality", claim_id="claim-1")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["doi"], "10.1000/cardiac.2024.1")
        self.assertIn("Mortality risk increases", hits[0]["abstract"])
        self.assertEqual(hits[0]["paper_kind"], "review")

    def test_parse_arxiv_feed_extracts_categories(self) -> None:
        feed_text = (FIXTURES / "arxiv_feed.xml").read_text(encoding="utf-8")
        hits = parse_arxiv_feed(feed_text, "single-cell atlas integration benchmark", claim_id="claim-2")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["source_id"], "2404.12345")
        self.assertIn("q-bio.GN", hits[0]["categories"])
        self.assertEqual(hits[0]["paper_kind"], "preprint")

    def test_parse_biorxiv_payload_extracts_abstract(self) -> None:
        payload = json.loads((FIXTURES / "biorxiv_details.json").read_text(encoding="utf-8"))
        hits = parse_biorxiv_payload(payload, "single-cell atlas integration benchmark", claim_id="claim-2")
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["doi"], "10.1101/2024.04.01.123456")
        self.assertIn("fibrotic heart disease", hits[0]["abstract"])
        self.assertEqual(hits[0]["paper_kind"], "preprint")


if __name__ == "__main__":
    unittest.main()
