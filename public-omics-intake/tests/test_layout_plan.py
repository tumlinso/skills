from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from plan_layout import build_layout_plan, materialize_layout


class LayoutPlanTests(unittest.TestCase):
    def test_dry_run_plan_does_not_create_directories(self) -> None:
        records = [{"source": "geo", "primary_accession": "GSE171555"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = build_layout_plan(tmpdir, "Liver Atlas", records, "processed")
            project_root = Path(plan["project_paths"]["project_root"])
            self.assertFalse(project_root.exists())

    def test_materialize_layout_creates_expected_paths(self) -> None:
        records = [{"source": "sra", "primary_accession": "PRJNA720779"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = build_layout_plan(tmpdir, "Heart Project", records, "metadata")
            materialize_layout(plan)
            self.assertTrue(Path(plan["project_paths"]["project_root"]).exists())
            self.assertTrue(Path(plan["datasets"][0]["runinfo_dir"]).exists())


if __name__ == "__main__":
    unittest.main()
