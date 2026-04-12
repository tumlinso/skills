import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "detect_figure_context.py"
FIXTURES = ROOT / "tests" / "figure_fixtures"


def run_detector(name: str, *extra_args: str) -> dict:
    fixture = FIXTURES / name
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(fixture), *extra_args],
        capture_output=True,
        check=True,
        text=True,
    )
    return json.loads(result.stdout)


class DetectFigureContextTests(unittest.TestCase):
    def test_existing_figure_convention_is_preserved(self) -> None:
        data = run_detector("existing_convention")
        self.assertEqual(data["primary_manuscript"], "main.qmd")
        self.assertEqual(data["figure_layout"]["status"], "existing")
        self.assertEqual(data["figure_layout"]["root_dir"], "figures")
        self.assertEqual(data["figure_layout"]["data_dir"], "figures/generated/data")
        self.assertEqual(data["figure_layout"]["schematic_dir"], "figures/generated/schematics")

    def test_mode_detection_prefers_data_when_inputs_are_present(self) -> None:
        data = run_detector(
            "minimal_repo",
            "--description",
            "workflow overview figure",
            "--input",
            "results/qc_summary.csv",
        )
        self.assertEqual(data["suggested_mode"], "data-figure")

    def test_existing_data_side_still_reserves_schematic_sibling_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "main.qmd").write_text(
                "---\n"
                'title: "Path Resolution Fixture"\n'
                "format:\n"
                "  pdf: default\n"
                "---\n\n"
                "## Results\n\n"
                "Figure paths should stay mode-specific.\n",
                encoding="utf-8",
            )
            (repo / "figures/generated/data").mkdir(parents=True)
            (repo / "figures/scripts/data").mkdir(parents=True)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(repo)],
                capture_output=True,
                check=True,
                text=True,
            )
            data = json.loads(result.stdout)
            self.assertEqual(data["figure_layout"]["schematic_dir"], "figures/generated/schematics")
            self.assertEqual(data["figure_layout"]["schematic_script_dir"], "figures/scripts/schematics")


if __name__ == "__main__":
    unittest.main()
