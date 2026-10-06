#!/usr/bin/env python3
"""Contract tests for portable campaign identity and frozen protocol evidence."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_campaign_evidence as exporter  # noqa: E402
import refresh_manifest as refresher  # noqa: E402
import validate_atlas as validator  # noqa: E402


class CampaignEvidenceContracts(unittest.TestCase):
    def test_unrelated_complete_campaign_is_rejected(self):
        config = {"campaign_key": "a" * 64}
        summary = {"campaign_key": "a" * 64}
        audit = {"campaign_key": "a" * 64}
        acceptance = {"source_commit": exporter.SOURCE_COMMIT,
                      "summary_complete": True, "blockers": [],
                      "e39_apparent_crossover_uncertainty": {
                          "method": "unpaired bootstrap median difference, 10000 resamples",
                          "confidence": 0.95, "established_crossover": False}}
        with self.assertRaisesRegex(ValueError, "campaign key"):
            exporter.validate_campaign_identity(config, summary, audit, acceptance)

    def test_portable_case_keeps_counts_without_raw_vectors(self):
        case = {"configuration": {"size": 128}, "status": "GPU_RUN",
                "checks": {"valid": True}, "metrics": {"median_ms": 0.2},
                "limitations": [], "samples": {"event_ms": [0.1, 0.2], "setup_ms": [0.03]}}
        compact = exporter.compact_case(case)
        self.assertNotIn("samples", compact)
        self.assertEqual(compact["raw_sample_counts"], {"event_ms": 2, "setup_ms": 1})
        self.assertEqual(compact["metrics"], case["metrics"])

    def test_archived_question_through_record_body_detects_edit(self):
        source = ("# E00\n**Question:** Which operation?\n\n"
                  "**Setup:** Fixed\n**Record:** Keep numeric and access details.\n")
        changed = source.replace("Fixed", "Changed")
        expected = exporter.hashlib.sha256(
            exporter.extract_original_protocol_body(source).encode("utf-8")
        ).hexdigest()
        self.assertEqual(validator.protocol_body_sha256(source), expected)
        self.assertNotEqual(validator.protocol_body_sha256(changed), expected)

    def test_status_or_campaign_provenance_mismatch_is_rejected(self):
        campaign = "b" * 64
        card_hash = "c" * 64
        body_hash = "d" * 64
        provenance = {"campaign_key": validator.CAMPAIGN_KEY,
                      "source_commit": validator.SOURCE_COMMIT,
                      "raw_artifacts_in_git": False,
                      "experiment_archive_anchors": {"E00": {
                          "original_card_sha256": card_hash,
                          "original_protocol_body_sha256": body_hash}}}
        summary = {"experiment": "E00", "status": "CPU_ONLY"}
        self.assertTrue(validator.evidence_matches_status(
            "E00", "CPU_ONLY", summary, provenance, card_hash, body_hash))
        self.assertFalse(validator.evidence_matches_status(
            "E00", "GPU_RUN", summary, provenance, card_hash, body_hash))
        provenance["campaign_key"] = campaign
        self.assertFalse(validator.evidence_matches_status(
            "E00", "CPU_ONLY", summary, provenance, card_hash, body_hash))

    def test_validator_scan_excludes_only_runtime_projections_and_own_report(self):
        markdown = set(validator.scoped_files(".md"))
        json_files = set(validator.scoped_files(".json"))
        self.assertNotIn(validator.ROOT / "todos.md", markdown)
        self.assertNotIn(validator.ROOT / "todo-status.md", markdown)
        self.assertNotIn(validator.ROOT / "experiments/evidence/v100-20261006/VALIDATION.json",
                         json_files)
        self.assertIn(validator.EVIDENCE / "E00.json", json_files)
        self.assertIn(validator.EVIDENCE / "provenance.json", json_files)

    def test_compiled_status_comes_from_portable_receipt_without_raw_run(self):
        receipt_hash = "a" * 64
        provenance = {"cuda_compiled": True,
                      "campaign_input_sha256": {"build.json": receipt_hash},
                      "campaign_identity": {"build": {
                          "returncode": 0, "receipt_sha256": receipt_hash,
                          "binary_sha256": {"atlas": "b" * 64}}}}
        self.assertTrue(refresher.portable_cuda_compiled(provenance))
        with tempfile.TemporaryDirectory() as temp:
            raw = Path(temp) / "build.json"
            raw.write_text("mismatched local file", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "disagrees"):
                refresher.portable_cuda_compiled(provenance, raw)


if __name__ == "__main__":
    unittest.main()
