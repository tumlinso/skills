import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


class I10DonorReceiptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.path = ROOT / "docs" / "workflow_foundation_v2" / "integration" / "WF2-DONOR.json"
        cls.receipt = json.loads(cls.path.read_text(encoding="utf-8"))

    def test_inventory_is_complete_and_content_addressed(self) -> None:
        inventory_ref = self.receipt["inventory"]
        inventory_path = ROOT / inventory_ref["path"]
        self.assertEqual(hashlib.sha256(inventory_path.read_bytes()).hexdigest(), inventory_ref["sha256"])
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(inventory["tracked_file_count"], len(inventory["tracked_files"]))
        self.assertGreater(inventory["tracked_file_count"], 100)

    def test_producer_completion_is_explicit_and_authority_scoped(self) -> None:
        self.assertEqual(self.receipt["authority"]["project_uuid"], "460468fe-ee72-4a64-a565-87cfec640d0c")
        producers = {item["task_id"]: item for item in self.receipt["producers"]}
        self.assertEqual(set(producers), {"SK-WF2-A03", "SK-WF2-V01"})
        self.assertTrue(all(item["state"] == "completed" and item["observed_revision"] > 0 for item in producers.values()))

    def test_receipt_is_not_self_referential(self) -> None:
        self.assertNotIn("commit", self.receipt)
        self.assertNotIn("sha256", self.receipt.get("authority", {}))
        policy = self.receipt["source_identity_policy"]
        self.assertIn("never embeds its own Git or file digest", policy)
        self.assertFalse(self.receipt["preservation"]["maintained_donor_removed"])


if __name__ == "__main__":
    unittest.main()
