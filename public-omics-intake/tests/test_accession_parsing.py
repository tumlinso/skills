from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from common import accession_type, geo_bucket, normalize_accession, parse_request_description


class AccessionParsingTests(unittest.TestCase):
    def test_supported_accessions(self) -> None:
        self.assertEqual(accession_type("GSE171555"), "geo-series")
        self.assertEqual(accession_type("SRR123456"), "sra-run")
        self.assertEqual(normalize_accession("prjna720779"), "PRJNA720779")

    def test_geo_bucket(self) -> None:
        self.assertEqual(geo_bucket("GSE171555"), "GSE171nnn")
        self.assertEqual(geo_bucket("GSM12345"), "GSM12nnn")

    def test_request_defaults_do_not_require_raw(self) -> None:
        spec = parse_request_description("adult human liver single-cell atlas")
        self.assertFalse(spec["raw_files_required"])
        self.assertTrue(spec["processed_files_acceptable"])


if __name__ == "__main__":
    unittest.main()
