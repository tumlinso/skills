from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS_DIR))

from build_manifest import build_manifest
from query_sra import normalize_sra_records


class ManifestGenerationTests(unittest.TestCase):
    def test_selected_manifest_filters_accessions(self) -> None:
        records = json.loads((FIXTURE_DIR / "rank_candidates.json").read_text())
        manifest = build_manifest(
            query_spec={"description": "test"},
            candidates=records,
            selected_accessions=["GSE171555"],
        )
        self.assertEqual(manifest["dataset_count"], 1)
        self.assertEqual(manifest["selected_datasets"][0]["primary_accession"], "GSE171555")

    def test_sra_normalization_preserves_run_metadata(self) -> None:
        rows = []
        with (FIXTURE_DIR / "sra_runinfo.tsv").open("r", encoding="utf-8") as handle:
            headers = handle.readline().strip().split("\t")
            for line in handle:
                values = line.strip().split("\t")
                rows.append(dict(zip(headers, values)))
        studies, runs = normalize_sra_records(rows)
        self.assertEqual(len(studies), 1)
        self.assertEqual(studies[0]["primary_accession"], "PRJNA720779")
        self.assertEqual(len(runs), 2)


if __name__ == "__main__":
    unittest.main()
