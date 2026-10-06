"""Verify the PA1 supplier handoff against the current source bytes.

These checks are deliberately source-only: they hash files and inspect JSON and
Markdown contracts. They do not import or start the local worker, model server,
CUDA controller, or any Project Control workflow service.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from typing import Any, Iterable


SKILLS_ROOT = Path("/home/tumlinson/.agents/skills").resolve()
PROJECT_CONTROL_ROOT = Path("/home/tumlinson/project-control").resolve()
DEFAULT_MANIFEST = SKILLS_ROOT / "docs/pa1/runtime-handoff.json"
MANIFEST_PATH = Path(os.environ.get("PA1_HANDOFF_MANIFEST", DEFAULT_MANIFEST)).resolve()


class HandoffError(AssertionError):
    """Raised when handoff evidence does not match its claimed source."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _repo_root(repository: str) -> Path:
    roots = {
        "skills": SKILLS_ROOT,
        "project-control": PROJECT_CONTROL_ROOT,
    }
    try:
        return roots[repository]
    except KeyError as exc:
        raise HandoffError(f"unknown repository identity: {repository}") from exc


def _source_identity_path(relative: str) -> tuple[Path, str]:
    """Resolve the manifest's repository-prefixed source identity key."""
    parts = Path(relative).parts
    if len(parts) < 2 or parts[0] not in {"skills", "project-control"}:
        if parts and parts[0] == "docs":
            # The handoff contract is a Project Control-owned document.
            return PROJECT_CONTROL_ROOT.joinpath(*parts), "project-control"
        raise HandoffError(f"source identity path lacks a repository prefix: {relative}")
    return _repo_root(parts[0]).joinpath(*parts[1:]), parts[0]


def _assert_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise HandoffError(f"{label} is missing: {path}")
    actual = _sha256(path)
    if actual != expected:
        raise HandoffError(f"{label} hash mismatch: {path}")


def _git_status(root: Path, relative: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "status", "--short", "--", relative],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.rstrip("\n")


def _assert_inventory_files(entries: Iterable[dict[str, Any]], root: Path) -> None:
    """Check a supplier inventory rooted at a disposable or actual source tree."""
    root = root.resolve()
    seen: set[str] = set()
    for entry in entries:
        relative = str(entry.get("path", ""))
        if not relative or relative in seen:
            raise HandoffError(f"missing or duplicate supplier path: {relative!r}")
        seen.add(relative)
        candidate = (root / relative).resolve()
        if candidate != root and root not in candidate.parents:
            raise HandoffError(f"supplier path escapes source root: {relative}")
        _assert_hash(candidate, str(entry.get("sha256", "")), "supplier file")
        if "bytes" in entry and candidate.stat().st_size != entry["bytes"]:
            raise HandoffError(f"supplier file byte count mismatch: {relative}")


def _assert_exclusions(exclusions: list[dict[str, Any]]) -> None:
    by_id = {str(item.get("id", "")): item for item in exclusions}
    required = {
        "todo-orchestrator": "todo-orchestrator/",
        "cuda": "cuda/",
        "cpp-context-compiler": "cpp-context-compiler/",
    }
    if len(by_id) != len(exclusions):
        raise HandoffError("exclusion IDs must be unique")
    for identity, path in required.items():
        item = by_id.get(identity)
        if item is None:
            raise HandoffError(f"independent authority exclusion missing: {identity}")
        if item.get("path") != path:
            raise HandoffError(f"{identity} exclusion path changed")
        if not item.get("authority") or not item.get("disposition"):
            raise HandoffError(f"{identity} exclusion lacks authority or disposition")
        if "exclud" not in str(item["disposition"]).lower():
            raise HandoffError(f"{identity} is not explicitly excluded from transfer")


def _assert_consumer_coverage(consumers: list[dict[str, Any]], *, verify_source_hashes: bool = True) -> None:
    keys = [(str(c.get("repository", "")), str(c.get("path", ""))) for c in consumers]
    if len(keys) != len(set(keys)):
        raise HandoffError("consumer inventory contains duplicate repository/path entries")
    present = set(keys)
    required = {
        ("skills", "integrations/as1_release.py"),
        ("skills", "integrations/native-skill-catalog.json"),
        ("skills", "tests/as1/test_sk_as1_gpu.py"),
        ("project-control", "src/project_control/adapters/local_worker.py"),
        ("project-control", "src/project_control/as1_jobs.py"),
        ("project-control", "tests/test_installer.py"),
    }
    missing = sorted(required - present)
    if missing:
        raise HandoffError(f"consumer inventory omits required live consumers: {missing}")
    for consumer in consumers:
        repository = str(consumer.get("repository", ""))
        path = str(consumer.get("path", ""))
        if not consumer.get("references"):
            raise HandoffError(f"consumer has no source references: {repository}:{path}")
        if verify_source_hashes:
            target = _repo_root(repository) / path
            _assert_hash(target, str(consumer.get("sha256", "")), "consumer source")
        for reference in consumer["references"]:
            if not isinstance(reference.get("line"), int) or not reference.get("symbol"):
                raise HandoffError(f"consumer reference is incomplete: {repository}:{path}")
            if not reference.get("required_transition"):
                raise HandoffError(f"consumer transition is unspecified: {repository}:{path}")
            if verify_source_hashes:
                lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
                line_number = reference["line"]
                if line_number < 1 or line_number > len(lines) or str(reference["symbol"]).strip() not in lines[line_number - 1]:
                    raise HandoffError(f"consumer source reference does not match {repository}:{path}:{line_number}")


def _assert_manifest(data: dict[str, Any]) -> None:
    if data.get("format") != "pa1-runtime-handoff/1":
        raise HandoffError("unexpected runtime handoff format")
    if Path(str(data.get("source_root", ""))).resolve() != SKILLS_ROOT:
        raise HandoffError("manifest source_root does not identify the canonical Skills checkout")
    if data.get("source_commit") != _git_head(SKILLS_ROOT):
        raise HandoffError("manifest source_commit is not the current Skills HEAD")

    identity = data.get("source_identity")
    if not isinstance(identity, dict) or not identity:
        raise HandoffError("source_identity must be a non-empty path-to-hash map")
    for relative, digest in identity.items():
        path, _ = _source_identity_path(str(relative))
        _assert_hash(path, str(digest), "source identity")

    supplier_files = data.get("supplier_files")
    if not isinstance(supplier_files, list) or not supplier_files:
        raise HandoffError("supplier_files must be a non-empty inventory")
    _assert_inventory_files(supplier_files, SKILLS_ROOT)
    supplier_paths = {str(item["path"]) for item in supplier_files}
    required = {
        "local-coding-worker/config/production-profile.toml",
        "local-coding-worker/config/host-profile.example.toml",
        "local-coding-worker/scripts/local_worker.py",
        "local-coding-worker/scripts/worker_core.py",
        "local-coding-worker/agents/openai.yaml",
    }
    if not required <= supplier_paths:
        raise HandoffError(f"supplier inventory misses runtime config or entrypoints: {sorted(required - supplier_paths)}")
    actual_schemas = {
        f"local-coding-worker/schemas/{p.name}"
        for p in (SKILLS_ROOT / "local-coding-worker/schemas").glob("*.schema.json")
    }
    inventoried_schemas = {p for p in supplier_paths if p.startswith("local-coding-worker/schemas/")}
    if actual_schemas != inventoried_schemas:
        raise HandoffError(
            f"JSON schema inventory differs from source; missing={sorted(actual_schemas-inventoried_schemas)}, "
            f"extra={sorted(inventoried_schemas-actual_schemas)}"
        )
    actual_configs = {
        path.relative_to(SKILLS_ROOT).as_posix()
        for path in (SKILLS_ROOT / "local-coding-worker/config").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    inventoried_configs = {
        path for path in supplier_paths if path.startswith("local-coding-worker/config/")
    }
    if actual_configs != inventoried_configs:
        raise HandoffError(
            f"runtime config inventory differs from source; missing={sorted(actual_configs-inventoried_configs)}, "
            f"extra={sorted(inventoried_configs-actual_configs)}"
        )
    actual_script_entrypoints = {
        path.relative_to(SKILLS_ROOT).as_posix()
        for path in (SKILLS_ROOT / "local-coding-worker/scripts").rglob("*.py")
        if "__pycache__" not in path.parts
    }
    inventoried_script_entrypoints = {
        path for path in supplier_paths
        if path.startswith("local-coding-worker/scripts/") and path.endswith(".py") and "/__pycache__/" not in path
    }
    if actual_script_entrypoints != inventoried_script_entrypoints:
        raise HandoffError(
            f"CLI/worker entrypoint inventory differs from source; missing={sorted(actual_script_entrypoints-inventoried_script_entrypoints)}, "
            f"extra={sorted(inventoried_script_entrypoints-actual_script_entrypoints)}"
        )
    for transfer_set in data.get("allowed_transfer_sets", []):
        for path in transfer_set.get("paths", []):
            if path not in supplier_paths:
                raise HandoffError(f"transfer set names an un-inventoried supplier file: {path}")

    receiver_files = data.get("receiver_files")
    if not isinstance(receiver_files, list) or not receiver_files:
        raise HandoffError("receiver_files must identify the receiving contract")
    receiver_contract = None
    for item in receiver_files:
        path = PROJECT_CONTROL_ROOT / str(item.get("path", ""))
        _assert_hash(path, str(item.get("sha256", "")), "receiver contract")
        if item.get("path") == "docs/pa1/runtime-ownership.md":
            receiver_contract = path
    if receiver_contract is None:
        raise HandoffError("receiver inventory omits docs/pa1/runtime-ownership.md")
    contract = receiver_contract.read_text(encoding="utf-8").lower()
    constraints = data.get("handoff_constraints", {})
    transition = str(constraints.get("legacy_transition", "")).lower()
    if "one-way compatibility forwarding" not in contract or "no receiver-to-skills-to-receiver" not in contract:
        raise HandoffError("receiver contract does not establish one-way forwarding and a no-cycle rule")
    if "one-way" not in transition or "no receiver-to-skills-to-receiver" not in transition:
        raise HandoffError("manifest transition constraints disagree with receiver contract")
    if constraints.get("module_identity") != "local_worker.* remains the single canonical runtime import identity after receiver adoption":
        raise HandoffError("manifest does not preserve the canonical local_worker module identity")

    _assert_exclusions(data.get("exclusions", []))
    consumers = data.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        raise HandoffError("consumers must be a non-empty inventory")
    _assert_consumer_coverage(consumers)

    stale = data.get("stale_release", {})
    if not stale.get("release_id") or stale.get("matches") is not False:
        raise HandoffError("stale paired release must be explicitly identified as non-matching")
    if stale.get("pinned_sha256") == stale.get("current_sha256"):
        raise HandoffError("stale paired release does not distinguish pinned and current source")
    if stale.get("qualification_record_matches_current") is not False:
        raise HandoffError("historical qualification is incorrectly treated as current")
    _assert_hash(SKILLS_ROOT / str(stale.get("manifest_path", "")), str(stale.get("manifest_sha256", "")), "paired release manifest")
    _assert_hash(SKILLS_ROOT / str(stale.get("current_path", "")), str(stale.get("current_sha256", "")), "current paired-release source")
    _assert_hash(
        SKILLS_ROOT / str(stale.get("qualification_record_path", "")),
        str(stale.get("qualification_record_sha256", "")),
        "historical qualification record",
    )
    if not any(word in str(stale.get("qualification", "")).lower() for word in ("stale", "historical", "refresh")):
        raise HandoffError("stale paired release lacks an explicit freshness qualification")

    dirty = data.get("baseline_dirty_hashes", [])
    catalog = next((item for item in dirty if item.get("path") == "skills/integrations/native-skill-catalog.json"), None)
    if catalog is None:
        raise HandoffError("baseline does not preserve the dirty native Skills catalog")
    _assert_hash(SKILLS_ROOT / "integrations/native-skill-catalog.json", str(catalog.get("sha256", "")), "dirty catalog")
    if not str(catalog.get("git_status", "")).strip():
        raise HandoffError("dirty catalog is not identified as dirty in the baseline")
    if _git_status(SKILLS_ROOT, "integrations/native-skill-catalog.json")[:2] != catalog["git_status"]:
        raise HandoffError("native Skills catalog working-tree status changed since the recorded baseline")
    if not catalog.get("preservation_rule") or constraints.get("dirty_catalog_must_remain_untouched") is not True:
        raise HandoffError("dirty catalog preservation rule is missing")


def _git_head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class RuntimeHandoffActualSourceTests(unittest.TestCase):
    def test_manifest_matches_hashed_actual_supplier_source(self) -> None:
        self.assertTrue(MANIFEST_PATH.is_file(), f"handoff manifest is missing: {MANIFEST_PATH}")
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        _assert_manifest(data)

    def test_modified_supplier_file_is_rejected_in_disposable_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="pa1-handoff-modified-") as temporary:
            root = Path(temporary)
            relative = Path("local-coding-worker/config/production-profile.toml")
            target = root / relative
            target.parent.mkdir(parents=True)
            target.write_bytes(b"profile = 'original'\n")
            entry = {"path": relative.as_posix(), "sha256": _sha256(target), "bytes": target.stat().st_size}
            _assert_inventory_files([entry], root)
            target.write_bytes(b"profile = 'modified'\n")
            with self.assertRaisesRegex(HandoffError, "hash mismatch"):
                _assert_inventory_files([entry], root)

    def test_each_domain_authority_exclusion_is_required_independently(self) -> None:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        exclusions = copy.deepcopy(manifest["exclusions"])
        _assert_exclusions(exclusions)
        exclusions = [item for item in exclusions if item["id"] != "todo-orchestrator"]
        with self.assertRaisesRegex(HandoffError, "todo-orchestrator"):
            _assert_exclusions(exclusions)

    def test_missing_live_consumer_is_rejected_in_manifest_copy(self) -> None:
        manifest_copy = copy.deepcopy(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
        baseline = manifest_copy["consumers"]
        _assert_consumer_coverage(baseline, verify_source_hashes=False)
        manifest_copy["consumers"] = [
            c for c in baseline if c["path"] != "integrations/native-skill-catalog.json"
        ]
        with self.assertRaisesRegex(HandoffError, "integrations/native-skill-catalog.json"):
            _assert_consumer_coverage(manifest_copy["consumers"], verify_source_hashes=False)

    def test_copied_manifest_rejects_missing_cuda_qualification_consumer(self) -> None:
        manifest_copy = copy.deepcopy(json.loads(MANIFEST_PATH.read_text(encoding="utf-8")))
        consumers = manifest_copy["consumers"]
        _assert_consumer_coverage(consumers, verify_source_hashes=False)
        manifest_copy["consumers"] = [
            c for c in consumers
            if not (c["repository"] == "skills" and c["path"] == "tests/as1/test_sk_as1_gpu.py")
        ]
        with self.assertRaisesRegex(HandoffError, "test_sk_as1_gpu.py"):
            _assert_consumer_coverage(manifest_copy["consumers"], verify_source_hashes=False)

if __name__ == "__main__":
    unittest.main()
