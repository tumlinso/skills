import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "map_manuscript.py"
FIXTURES = ROOT / "tests" / "paper_fixtures"


def run_mapper(name: str) -> dict:
    fixture = FIXTURES / name
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture)],
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout)


class MapManuscriptTests(unittest.TestCase):
    def test_single_file_manuscript_prefers_main_qmd(self) -> None:
        data = run_mapper("single_file_paper")
        self.assertEqual(data["primary_manuscript"], "main.qmd")
        self.assertEqual(data["quarto_config"], "_quarto.yml")
        self.assertEqual(data["docs_role"]["status"], "output")
        bibliography_paths = {item["path"] for item in data["bibliography_files"]}
        include_paths = {item["path"] for item in data["include_files"]}
        self.assertIn("references.bib", bibliography_paths)
        self.assertIn("preamble.tex", include_paths)

    def test_split_manuscript_detects_section_files(self) -> None:
        data = run_mapper("split_paper")
        self.assertEqual(data["primary_manuscript"], "main.qmd")
        self.assertIn("sections/01_intro/_intro.qmd", data["section_files"])
        self.assertIn("sections/02_results/_results.qmd", data["section_files"])

    def test_docs_is_not_assumed_to_be_source(self) -> None:
        data = run_mapper("docs_ambiguous")
        self.assertEqual(data["primary_manuscript"], "main.qmd")
        self.assertEqual(data["docs_role"]["status"], "ambiguous")


if __name__ == "__main__":
    unittest.main()
