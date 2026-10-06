#!/usr/bin/env python3
"""Source-less integrity tests for the installed V100 atlas bundle."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]
ATLAS_REL = Path("cuda/references/architectures/volta/v100_atlas")
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_skill_bundle as bundle  # noqa: E402


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AtlasBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = REPO_ROOT / ATLAS_REL
        cls.inventory = json.loads((cls.atlas / "import-map.json").read_text())
        cls.corpus = json.loads((REPO_ROOT / "cuda/.project-control-corpus.json").read_text())

    def test_deployed_bundle_validates_without_source_checkout(self):
        self.assertEqual([], bundle.validate(REPO_ROOT))

    def test_complete_card_inventory_and_body_preservation(self):
        self.assertEqual(190, self.inventory["counts"]["cards"])
        self.assertEqual(
            {"references": 16, "mechanisms": 52, "compositions": 40, "experiments": 40, "sources": 42},
            {key: self.inventory["counts"][key] for key in ("references", "mechanisms", "compositions", "experiments", "sources")},
        )
        self.assertEqual(190, len(self.inventory["cards"]))
        for identifier, item in self.inventory["cards"].items():
            original = self.atlas / bundle.snapshot_path(item["source_path"])
            imported = self.atlas / item["path"]
            self.assertTrue(original.is_file(), identifier)
            self.assertTrue(imported.is_file(), identifier)
            source_text = original.read_text(encoding="utf-8")
            expected = bundle.rewrite_local_links(
                source_text,
                Path("/source") / item["source_path"],
                Path(item["path"]),
                Path("/source"),
                self.inventory["mapping"]["source_to_bundle"],
            )
            self.assertEqual(expected, imported.read_text(encoding="utf-8"), identifier)
            self.assertIn(identifier, imported.read_text(encoding="utf-8").splitlines()[0], identifier)

    def test_original_archives_and_campaign_identity_are_byte_verified(self):
        compendium = self.atlas / self.inventory["archive"]["compendium"]
        zip_path = self.atlas / self.inventory["archive"]["zip"]
        prior_graph = self.atlas / self.inventory["archive"]["prior_corpus"]
        self.assertEqual(self.inventory["archive"]["compendium_sha256"], sha(compendium))
        self.assertEqual(self.inventory["archive"]["zip_sha256"], sha(zip_path))
        old = json.loads(prior_graph.read_text())
        self.assertEqual(237, len(old["resources"]))
        self.assertEqual(929, len(old["relationships"]))
        provenance = json.loads((self.atlas / "experiments/evidence/v100-20261006/provenance.json").read_text())
        self.assertEqual("f223c51dcfacab602e9bc68b3e65cc75730dc7f8", provenance["source_commit"])
        self.assertEqual("5c1f805db80a81f7476ede8292abba69821d104f", provenance["original_protocol_archive_commit"])
        self.assertFalse(provenance["raw_artifacts_in_git"])
        with zipfile.ZipFile(zip_path) as archive:
            for index in range(40):
                identifier = f"E{index:02d}"
                original = archive.read(f"v100_atlas/experiments/{identifier}.md").decode("utf-8")
                self.assertEqual(provenance["original_card_sha256"][identifier], hashlib.sha256(original.encode()).hexdigest())
                self.assertEqual(provenance["original_protocol_body_sha256"][identifier], bundle.protocol_body_sha256(original))

    def test_corpus_adds_atlas_graph_and_preserves_both_prior_graphs(self):
        imported = json.loads((self.atlas / self.inventory["archive"]["prior_corpus"]).read_text())
        baseline = json.loads((self.atlas / self.inventory["workspace_baseline"]["archive"]).read_text())
        resources = {item["id"]: item for item in self.corpus["resources"]}
        edges = {(item["from"], item["to"], item["type"]) for item in self.corpus["relationships"]}
        for item in baseline["resources"]:
            actual = resources[item["id"]]
            self.assertEqual({key: value for key, value in item.items() if key != "sha256"}, {key: value for key, value in actual.items() if key != "sha256"})
            if actual.get("sha256") != item.get("sha256"):
                target = REPO_ROOT / "cuda" / item.get("path", "")
                self.assertTrue(target.is_file())
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), actual.get("sha256"))
        for item in imported["resources"]:
            self.assertIn(item["id"], resources)
            self.assertTrue(resources[item["id"]]["path"].startswith("references/architectures/volta/v100_atlas/"))
            self.assertTrue((REPO_ROOT / "cuda" / resources[item["id"]]["path"]).is_file())
        for group in (baseline, imported):
            for edge in group["relationships"]:
                self.assertIn((edge["from"], edge["to"], edge["type"]), edges)
        self.assertGreaterEqual(len(self.corpus["resources"]), 110 + 237)
        self.assertGreaterEqual(len(self.corpus["relationships"]), 298 + 929)

    def test_gpu_measured_identity_does_not_include_cpu_or_unrun_records(self):
        statuses = self.inventory["counts"]["campaign_evidence_status"]
        self.assertEqual({"CPU_ONLY": 6, "GPU_RUN": 29, "NOT_RUN": 5}, statuses)
        resource_ids = {item["id"] for item in self.corpus["resources"]}
        for index in range(40):
            identifier = f"E{index:02d}"
            status = json.loads((self.atlas / f"experiments/evidence/v100-20261006/{identifier}.json").read_text())["status"]
            self.assertIn(f"atlas-result-{identifier}", resource_ids)
            self.assertEqual(status == "GPU_RUN", f"atlas-measured-{identifier}" in resource_ids)

    def test_validator_detects_body_tampering(self):
        with tempfile.TemporaryDirectory(prefix="atlas-bundle-corruption-") as temp:
            root = Path(temp)
            target = root / ATLAS_REL
            shutil.copytree(self.atlas, target)
            (root / "cuda").mkdir(exist_ok=True)
            shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", root / "cuda/.project-control-corpus.json")
            card = target / self.inventory["cards"]["M01"]["path"]
            card.write_text(card.read_text() + "\nUnapproved content change.\n")
            failures = bundle.validate(root)
            self.assertTrue(any("content or non-link wording changed" in failure for failure in failures), failures)

    def test_validator_checks_generated_payload_and_owned_hashes(self):
        for relative in (
            "CURRENT_STATUS.md",
            "experiments/evidence/v100-20261006/E33-raw-host-records.md",
            "CARD_CATALOG.md",
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory(prefix="atlas-owned-tamper-") as temp:
                root = Path(temp)
                atlas = root / ATLAS_REL
                shutil.copytree(self.atlas, atlas)
                (root / "cuda").mkdir(exist_ok=True)
                shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", root / "cuda/.project-control-corpus.json")
                target = atlas / relative
                target.write_bytes(target.read_bytes() + b"tamper")
                failures = bundle.validate(root)
                self.assertIn(f"owned import file hash mismatch: {relative}", failures)

    def test_validator_detects_import_map_sidecar_tampering(self):
        with tempfile.TemporaryDirectory(prefix="atlas-map-sidecar-") as temp:
            root = Path(temp)
            atlas = root / ATLAS_REL
            shutil.copytree(self.atlas, atlas)
            (root / "cuda").mkdir(exist_ok=True)
            shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", root / "cuda/.project-control-corpus.json")
            sidecar = atlas / "import-map.sha256"
            sidecar.write_text("0" * 64 + "\n")
            failures = bundle.validate(root)
            self.assertIn("import-map integrity sidecar missing or mismatched", failures)

    def test_pinned_git_object_ignores_dirty_checkout_and_rejects_untracked(self):
        with tempfile.TemporaryDirectory(prefix="atlas-pinned-source-") as temp:
            source = Path(temp)
            import subprocess
            subprocess.run(["git", "init", "-q", str(source)], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "add", "-A"], check=True)
            (source / "tracked.txt").write_bytes(b"pinned bytes")
            subprocess.run(["git", "-C", str(source), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-qm", "fixture"], check=True)
            commit = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            (source / "tracked.txt").write_bytes(b"dirty bytes")
            self.assertEqual(b"pinned bytes", bundle.pinned_source_bytes(source, "tracked.txt", commit))
            with self.assertRaises(ValueError):
                bundle.pinned_source_bytes(source, "untracked.txt", commit)

    def test_overwrite_guard_rejects_changed_owned_and_unowned_payloads(self):
        with tempfile.TemporaryDirectory(prefix="atlas-owned-payload-") as temp:
            root = Path(temp)
            owned = root / "known.md"
            owned.write_bytes(b"initial")
            ownership = {"known.md": bundle.sha256(b"initial")}
            owned.write_bytes(b"manual edit")
            with self.assertRaises(ValueError):
                bundle.write_imported(root, owned, b"replacement", ownership)
            unknown = root / "unknown.md"
            unknown.write_bytes(b"collision")
            with self.assertRaises(ValueError):
                bundle.write_imported(root, unknown, b"replacement", ownership)

    def test_importer_rejects_symlink_and_dangling_output_paths(self):
        with tempfile.TemporaryDirectory(prefix="atlas-symlink-output-") as temp:
            root = Path(temp)
            atlas = root / "atlas"
            atlas.mkdir()
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_bytes(b"unchanged")
            (atlas / "linked").symlink_to(outside, target_is_directory=True)
            (atlas / "dangling").symlink_to(outside / "missing", target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink in atlas output path"):
                bundle.write_imported(atlas, atlas / "linked/new-file", b"escape", {})
            with self.assertRaisesRegex(ValueError, "symlink in atlas output path"):
                bundle.write_imported(atlas, atlas / "dangling/new-file", b"escape", {})
            self.assertEqual(b"unchanged", sentinel.read_bytes())
            self.assertFalse((outside / "missing" / "new-file").exists())

    def test_validator_rejects_symlinked_repo_ancestor(self):
        with tempfile.TemporaryDirectory(prefix="atlas-validate-ancestor-") as temp:
            root = Path(temp)
            cuda = root / "cuda"
            (cuda / "references/architectures").mkdir(parents=True)
            external = root / "external"
            external.mkdir()
            (cuda / "references/architectures/volta").symlink_to(external, target_is_directory=True)
            failures = bundle.validate(root)
            self.assertEqual(1, len(failures), failures)
            self.assertTrue(failures[0].startswith("unsafe atlas path: symlink in repository output path"), failures)

    def test_real_build_rejects_source_snapshot_symlink_before_directory_writes(self):
        import subprocess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix="atlas-source-snapshot-symlink-") as temp:
            root = Path(temp)
            skill_root = root / "skill"
            atlas = skill_root / ATLAS_REL
            shutil.copytree(self.atlas, atlas)
            (skill_root / "cuda").mkdir(exist_ok=True)
            shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", skill_root / "cuda/.project-control-corpus.json")
            prior_graph = (self.atlas / self.inventory["archive"]["prior_corpus"]).read_bytes()
            baseline_graph = (self.atlas / self.inventory["workspace_baseline"]["archive"]).read_bytes()
            source_snapshot = atlas / "archive/source-snapshot"
            shutil.rmtree(source_snapshot)
            external = root / "external"
            external.mkdir()
            sentinel = external / "sentinel"
            sentinel.write_bytes(b"preserve")
            source_snapshot.symlink_to(external, target_is_directory=True)
            subprocess_check_output = subprocess.check_output
            def check_output(args, *call_args, **kwargs):
                if isinstance(args, (list, tuple)) and len(args) >= 4 and args[0:2] == ["git", "-C"] and Path(args[2]) == skill_root:
                    spec = args[-1]
                    if spec == "9581834:cuda/references/architectures/volta/v100_atlas/.project-control-corpus.json":
                        return prior_graph
                    if spec == f"{bundle.CORPUS_BASELINE_COMMIT}:cuda/.project-control-corpus.json":
                        return baseline_graph
                return subprocess_check_output(args, *call_args, **kwargs)
            with patch.object(bundle.subprocess, "check_output", side_effect=check_output):
                with self.assertRaisesRegex(ValueError, "symlink in atlas output path"):
                    bundle.build(
                        Path("/home/tumlinson/gpu_circuit_bending_atlas"),
                        self.atlas / self.inventory["archive"]["zip"],
                        skill_root,
                    )
            self.assertEqual(b"preserve", sentinel.read_bytes())
            self.assertEqual([sentinel], list(external.iterdir()))

    def test_real_build_rejects_symlinked_volta_ancestor_before_atlas_mkdir(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix="atlas-volta-ancestor-") as temp:
            root = Path(temp)
            skill_root = root / "skill"
            cuda_root = skill_root / "cuda"
            (cuda_root / "references/architectures").mkdir(parents=True)
            external = root / "external"
            external.mkdir()
            sentinel = external / "sentinel"
            sentinel.write_bytes(b"preserve")
            (cuda_root / "references/architectures/volta").symlink_to(external, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink in repository output path"):
                bundle.build(Path("/home/tumlinson/gpu_circuit_bending_atlas"), self.atlas / self.inventory["archive"]["zip"], skill_root)
            self.assertEqual(b"preserve", sentinel.read_bytes())
            self.assertEqual([sentinel], list(external.iterdir()))

    def test_real_build_rejects_symlinked_corpus_without_external_write(self):
        import subprocess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(prefix="atlas-corpus-symlink-") as temp:
            root = Path(temp)
            skill_root = root / "skill"
            atlas = skill_root / ATLAS_REL
            shutil.copytree(self.atlas, atlas)
            (skill_root / "cuda").mkdir(exist_ok=True)
            prior_graph = (self.atlas / self.inventory["archive"]["prior_corpus"]).read_bytes()
            baseline_graph = (self.atlas / self.inventory["workspace_baseline"]["archive"]).read_bytes()
            external = root / "external"
            external.mkdir()
            sentinel = external / "corpus.json"
            sentinel.write_bytes(b"preserve")
            (skill_root / "cuda/.project-control-corpus.json").symlink_to(sentinel)
            subprocess_check_output = subprocess.check_output
            def check_output(args, *call_args, **kwargs):
                if isinstance(args, (list, tuple)) and len(args) >= 4 and args[0:2] == ["git", "-C"] and Path(args[2]) == skill_root:
                    spec = args[-1]
                    if spec == "9581834:cuda/references/architectures/volta/v100_atlas/.project-control-corpus.json":
                        return prior_graph
                    if spec == f"{bundle.CORPUS_BASELINE_COMMIT}:cuda/.project-control-corpus.json":
                        return baseline_graph
                return subprocess_check_output(args, *call_args, **kwargs)
            with patch.object(bundle.subprocess, "check_output", side_effect=check_output):
                with self.assertRaisesRegex(ValueError, "symlink in repository output path"):
                    bundle.build(Path("/home/tumlinson/gpu_circuit_bending_atlas"), self.atlas / self.inventory["archive"]["zip"], skill_root)
            self.assertEqual(b"preserve", sentinel.read_bytes())

    def test_legacy_import_build_fails_closed_without_hash_manifest(self):
        import subprocess
        from unittest.mock import patch
        inventory = self.inventory
        old_graph = (self.atlas / inventory["archive"]["prior_corpus"]).read_bytes()
        baseline_graph = (self.atlas / inventory["workspace_baseline"]["archive"]).read_bytes()
        targets = [
            inventory["cards"]["M01"]["path"],
            "CURRENT_STATUS.md",
            "experiments/evidence/v100-20261006/E33-raw-host-records.md",
        ]
        with tempfile.TemporaryDirectory(prefix="atlas-legacy-build-") as temp:
            root = Path(temp)
            (root / "cuda").mkdir()
            shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", root / "cuda/.project-control-corpus.json")
            for index, relative in enumerate(targets):
                atlas_copy = root / f"case-{index}" / ATLAS_REL
                shutil.copytree(self.atlas, atlas_copy)
                (atlas_copy / "import-map.sha256").unlink()
                target = atlas_copy / relative
                original = target.read_bytes()
                target.write_bytes(original + b"manual edit")
                tampered = target.read_bytes()
                def check_output(args, *call_args, **kwargs):
                    if isinstance(args, (list, tuple)) and len(args) >= 4 and args[0:2] == ["git", "-C"] and Path(args[2]) == root / f"case-{index}":
                        spec = args[-1]
                        if spec == "9581834:cuda/references/architectures/volta/v100_atlas/.project-control-corpus.json":
                            return old_graph
                        if spec == f"{bundle.CORPUS_BASELINE_COMMIT}:cuda/.project-control-corpus.json":
                            return baseline_graph
                    return subprocess_check_output(args, *call_args, **kwargs)
                subprocess_check_output = subprocess.check_output
                with patch.object(bundle.subprocess, "check_output", side_effect=check_output):
                    with self.assertRaisesRegex(ValueError, "legacy import map has no owned-file hash manifest"):
                        bundle.build(
                            Path("/home/tumlinson/gpu_circuit_bending_atlas"),
                            self.atlas / inventory["archive"]["zip"],
                            root / f"case-{index}",
                        )
                self.assertEqual(tampered, target.read_bytes(), relative)
                self.assertFalse((atlas_copy / "import-map.sha256").exists())

    def test_pinned_archive_cannot_be_blessed_by_editing_import_map(self):
        with tempfile.TemporaryDirectory(prefix="atlas-map-tamper-") as temp:
            root = Path(temp)
            shutil.copytree(self.atlas, root / ATLAS_REL)
            (root / "cuda").mkdir(exist_ok=True)
            shutil.copy2(REPO_ROOT / "cuda/.project-control-corpus.json", root / "cuda/.project-control-corpus.json")
            atlas = root / ATLAS_REL
            changed = atlas / "archive/V100_ATLAS_FULL.source.txt"
            changed.write_bytes(changed.read_bytes() + b"tamper")
            inventory_path = atlas / "import-map.json"
            inventory = json.loads(inventory_path.read_text())
            inventory["archive"]["compendium_sha256"] = sha(changed)
            inventory_path.write_text(json.dumps(inventory))
            failures = bundle.validate(root)
            self.assertTrue(any("compendium missing or hash mismatch" in failure for failure in failures), failures)

    def test_catalog_and_portable_wrappers_are_reachable_and_not_raw_claims(self):
        start = (self.atlas / "START_HERE.md").read_text()
        self.assertIn("[complete card and resource catalog](CARD_CATALOG.md)", start)
        self.assertIn("[E33: ", (self.atlas / "CARD_CATALOG.md").read_text())
        for identifier in ("E33", "E34", "E35", "E36", "E38"):
            wrapper = (self.atlas / f"experiments/evidence/v100-20261006/{identifier}-raw-host-records.md").read_text()
            self.assertIn("raw host JSON capture is not included", wrapper)
            self.assertIn("portable", wrapper)

    def test_local_markdown_links_resolve_including_non_markdown_targets(self):
        failures = bundle.validate(REPO_ROOT)
        self.assertFalse([item for item in failures if "local Markdown link" in item], failures)


if __name__ == "__main__":
    unittest.main(verbosity=2)
