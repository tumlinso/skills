from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cuda_guidance import retrieve, validate_manifest  # noqa: E402


class GuidanceTests(unittest.TestCase):
    def test_manifest_preserves_entire_markdown_corpus(self) -> None:
        payload = json.loads((ROOT / "assets" / "cuda-markdown-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(ROOT, payload), [])
        expected = {"SKILL.md", *{path.relative_to(ROOT).as_posix() for path in (ROOT / "references").rglob("*.md")}}
        self.assertEqual({item["path"] for item in payload["files"]}, expected)

    def test_retrieval_is_exact_bounded_and_architecture_first(self) -> None:
        result = retrieve(ROOT, "volta occupancy registers", limit=3, token_budget=500)
        self.assertLessEqual(len(result["sections"]), 3)
        self.assertLessEqual(result["token_estimate"], 500)
        self.assertIn("volta", result["sections"][0]["tags"])
        for section in result["sections"]:
            lines = (ROOT / section["path"]).read_text(encoding="utf-8").splitlines(keepends=True)
            self.assertEqual(section["text"], "".join(lines[section["line_start"] - 1:section["line_end"]]))


if __name__ == "__main__":
    unittest.main()
