import json
import subprocess
import sys
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "extract_citation_gaps.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def run_extractor(name: str) -> dict:
    fixture = FIXTURES / name
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout)


class ExtractCitationGapTests(unittest.TestCase):
    def test_extracts_uncited_claims_and_skips_cited_sentences(self) -> None:
        data = run_extractor("citation_paper")
        sentences = [item["sentence"] for item in data["gaps"]]
        self.assertGreaterEqual(len(sentences), 3)
        self.assertIn("Our model reduces error by 35% across three datasets.", sentences)
        self.assertIn("Cardiac fibrosis is associated with high mortality.", sentences)
        self.assertIn("Single-cell atlases are widely used to study developmental trajectories.", sentences)
        self.assertNotIn(
            "Recent studies show that BRD4 disruption attenuates fibroblast activation [@brd4].",
            sentences,
        )


if __name__ == "__main__":
    unittest.main()
