import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAKE_DATA = ROOT / "scripts" / "make_data_figure.py"
MAKE_SCHEMATIC = ROOT / "scripts" / "make_schematic_figure.py"
UPDATE_SPEC = ROOT / "scripts" / "update_figure_spec.py"


class FigureSpecRoundtripTests(unittest.TestCase):
    def test_data_figure_spec_creation_and_update_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "main.qmd").write_text(
                "---\n"
                'title: "Roundtrip Fixture"\n'
                "format:\n"
                "  pdf: default\n"
                "---\n\n"
                "## Results\n\n"
                "Processed results live in this repo.\n",
                encoding="utf-8",
            )
            results_dir = repo / "results"
            results_dir.mkdir()
            (results_dir / "qc_summary.csv").write_text(
                "sample,value,group\nA,1.0,control\nB,2.0,treated\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(MAKE_DATA),
                    "--repo",
                    str(repo),
                    "--figure-id",
                    "fig-qc",
                    "--input",
                    "results/qc_summary.csv",
                    "--x",
                    "sample",
                    "--y",
                    "value",
                    "--plot-kind",
                    "bar",
                    "--no-render",
                ],
                capture_output=True,
                check=True,
                text=True,
            )
            spec_path = Path(result.stdout.strip())
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            self.assertEqual(spec["mode"], "data-figure")
            self.assertEqual(spec["created_with"]["skill"], "quarto-manuscript")
            self.assertEqual(spec["created_with"]["helper"], "make_data_figure.py")
            self.assertIn("results/qc_summary.csv", {item["path"] for item in spec["inputs"]})
            self.assertTrue((repo / spec["source_script"]).exists())

            subprocess.run(
                [
                    sys.executable,
                    str(UPDATE_SPEC),
                    str(spec_path),
                    "--add-output-format",
                    "pdf",
                    "--set",
                    'parameters.group="group"',
                ],
                capture_output=True,
                check=True,
                text=True,
            )
            updated = json.loads(spec_path.read_text(encoding="utf-8"))
            self.assertIn("pdf", updated["export_formats"])
            self.assertEqual(updated["parameters"]["group"], "group")
            self.assertIn("pdf", updated["outputs"])

    def test_schematic_spec_keeps_editable_svg_reference(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            (repo / "main.qmd").write_text(
                "---\n"
                'title: "Schematic Fixture"\n'
                "format:\n"
                "  pdf: default\n"
                "---\n\n"
                "## Introduction\n\n"
                "A workflow overview belongs here.\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(MAKE_SCHEMATIC),
                    "--repo",
                    str(repo),
                    "--figure-id",
                    "fig-overview",
                    "--description",
                    "sample collection -> profiling -> integration -> modeling",
                    "--no-render",
                ],
                capture_output=True,
                check=True,
                text=True,
            )
            spec_path = Path(result.stdout.strip())
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            self.assertEqual(spec["mode"], "schematic-figure")
            self.assertEqual(spec["created_with"]["skill"], "quarto-manuscript")
            self.assertEqual(spec["created_with"]["helper"], "make_schematic_figure.py")
            self.assertEqual(spec["source_editable"], spec["outputs"]["svg"])
            self.assertTrue((repo / spec["source_script"]).exists())


if __name__ == "__main__":
    unittest.main()
