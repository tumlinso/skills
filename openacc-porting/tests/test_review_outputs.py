from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARIZE = ROOT / "scripts" / "summarize_openacc_candidates.py"
GENERATE = ROOT / "scripts" / "generate_openacc_review.py"


class ReviewOutputTests(unittest.TestCase):
    def write_candidates(self, path: Path) -> None:
        path.write_text(
            json.dumps(
                [
                    {
                        "id": "stencil",
                        "location": "solver.cpp:88",
                        "compute_dense": True,
                        "stable_data_region": True,
                    },
                    {
                        "id": "prefix-edge",
                        "location": "graph.cpp:155",
                        "scan": True,
                        "indirect_indexing": True,
                    },
                    {
                        "id": "linked-walk",
                        "location": "graph.cpp:220",
                        "pointer_chasing": True,
                    },
                ],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def test_summary_json_and_markdown_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            candidates = tmpdir_path / "candidates.json"
            summary = tmpdir_path / "summary.json"
            review = tmpdir_path / "openacc-review.md"
            self.write_candidates(candidates)

            subprocess.run(
                [sys.executable, str(SUMMARIZE), "--input", str(candidates), "--format", "json", "--output", str(summary)],
                check=True,
                text=True,
            )
            data = json.loads(summary.read_text(encoding="utf-8"))
            self.assertEqual(data["counts"]["easy to port"], 1)
            self.assertEqual(data["counts"]["possible with restructuring"], 1)
            self.assertEqual(data["counts"]["poor OpenACC target"], 1)

            subprocess.run(
                [
                    sys.executable,
                    str(GENERATE),
                    "--scope",
                    "Sparse graph traversal",
                    "--candidate-json",
                    str(summary),
                    "--output",
                    str(review),
                ],
                check=True,
                text=True,
            )

            text = review.read_text(encoding="utf-8")
            self.assertIn("## Scope", text)
            self.assertIn("## Candidate Regions", text)
            self.assertIn("## Proposed Data-Region Plan", text)
            self.assertIn("## Staged Implementation Plan", text)
            self.assertIn("## Validation Checklist", text)
            self.assertIn("## Performance Risks", text)
            self.assertIn("## Benchmark Follow-On", text)

    def test_template_review_without_candidates_still_has_required_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            review = Path(tmpdir) / "openacc-review.md"
            subprocess.run(
                [sys.executable, str(GENERATE), "--scope", "Cold review", "--output", str(review)],
                check=True,
                text=True,
            )
            text = review.read_text(encoding="utf-8")
            self.assertIn("Cold review", text)
            self.assertIn("shared scenario contract", text)
            self.assertIn("correctness is stable", text)


if __name__ == "__main__":
    unittest.main()
