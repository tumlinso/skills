from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

from common import build_geo_download_plan
from query_geo import normalize_geo_record


class GeoUrlBuildingTests(unittest.TestCase):
    def test_geo_download_plan_for_series(self) -> None:
        plan = build_geo_download_plan("GSE171555")
        self.assertEqual(plan["root_ftp_path"], "/geo/series/GSE171nnn/GSE171555")
        urls = {item["label"]: item["url"] for item in plan["download_candidates"]}
        self.assertTrue(urls["soft"].endswith("/soft/GSE171555_family.soft.gz"))
        self.assertTrue(urls["miniml"].endswith("/miniml/GSE171555_family.xml.tgz"))

    def test_geo_record_normalization(self) -> None:
        doc = json.loads((FIXTURE_DIR / "geo_doc.json").read_text())
        record = normalize_geo_record(doc)
        self.assertEqual(record["primary_accession"], "GSE171555")
        self.assertIn("scrna-seq", record["modality"])
        self.assertTrue(record["processed_available"])


if __name__ == "__main__":
    unittest.main()
