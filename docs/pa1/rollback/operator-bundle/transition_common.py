"""Fail-closed helpers for the inert PA1 Skills transition operator scripts."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

STAGE_ROOT = Path(__file__).resolve().parent
MAP_PATH = STAGE_ROOT / "runtime-transition.json"


class TransitionError(RuntimeError):
    pass


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise TransitionError(f"invalid_json:{path}") from error
    if not isinstance(value, dict):
        raise TransitionError(f"json_object_required:{path}")
    return value


def safe_member(value: str) -> str:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not value or str(path) != value:
        raise TransitionError(f"unsafe_manifest_path:{value}")
    return value


def reject_symlink_components(root: Path, relative: str) -> Path:
    safe_member(relative)
    root = root.resolve(strict=True)
    current = root
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise TransitionError(f"symlink_path_component_rejected:{relative}")
    if root not in current.parents and current != root:
        raise TransitionError(f"path_escapes_root:{relative}")
    return current


@dataclass(frozen=True)
class Bundle:
    mapping: dict[str, Any]
    provenance: dict[str, Any]
    inventory: dict[str, Any]
    source_root: Path
    skill_root: Path
    candidate_root: Path
    archive_path: Path


def load_bundle() -> Bundle:
    mapping = read_json(MAP_PATH)
    if mapping.get("format") != "pa1-skills-runtime-transition-candidate/1":
        raise TransitionError("transition_map_format_invalid")
    inventory_path = Path(str(mapping.get("source_inventory_path", "")))
    inventory_raw = inventory_path.read_bytes()
    if sha256(inventory_raw) != mapping.get("source_inventory_sha256"):
        raise TransitionError("supplier_inventory_changed")
    inventory = json.loads(inventory_raw)
    if inventory.get("format") != "pa1-runtime-handoff/1":
        raise TransitionError("supplier_inventory_format_invalid")
    source_root = Path(str(mapping.get("source_root", ""))).resolve(strict=True)
    skill_root = source_root / "local-coding-worker"
    candidate_root = STAGE_ROOT / "runtime" / "local-coding-worker"
    provenance_path = STAGE_ROOT / str(mapping.get("rollback_provenance", ""))
    archive_path = STAGE_ROOT / str(mapping.get("rollback_archive", ""))
    provenance = read_json(provenance_path)
    if provenance.get("format") != "pa1-skills-runtime-rollback/1":
        raise TransitionError("rollback_provenance_format_invalid")
    if provenance.get("inventory_sha256") != mapping.get("source_inventory_sha256"):
        raise TransitionError("rollback_inventory_identity_mismatch")
    if sha256(archive_path.read_bytes()) != mapping.get("rollback_archive_sha256"):
        raise TransitionError("rollback_archive_hash_mismatch")
    return Bundle(mapping, provenance, inventory, source_root, skill_root, candidate_root, archive_path)


def archive_files(bundle: Bundle) -> dict[str, tuple[bytes, int]]:
    provenance = bundle.provenance
    expected: dict[str, tuple[str, int]] = {}
    for key, digest_key in (("archived_files", "archived_files"), ("excluded_unportable_bytecode", "excluded_unportable_bytecode")):
        for entry in provenance.get(key, []):
            rel = safe_member(str(entry.get("path", "")))
            if rel in expected:
                raise TransitionError(f"duplicate_rollback_provenance_path:{rel}")
            expected[rel] = (str(entry.get("sha256", "")), int(entry.get("bytes", -1)))
    supplier = {str(entry["path"]): entry for entry in bundle.inventory.get("supplier_files", [])}
    if set(expected) != set(supplier):
        raise TransitionError("rollback_provenance_inventory_coverage_mismatch")
    for rel, (digest, size) in expected.items():
        source = supplier[rel]
        if digest != source.get("sha256") or size != source.get("bytes"):
            raise TransitionError(f"rollback_provenance_source_identity_mismatch:{rel}")
    archived_expected = {
        f"local-coding-worker/{entry['path']}": (entry["sha256"], int(entry["bytes"]))
        for entry in provenance.get("archived_files", [])
    }
    payloads: dict[str, tuple[bytes, int]] = {}
    try:
        with tarfile.open(bundle.archive_path, "r:gz") as archive:
            seen: set[str] = set()
            for member in archive.getmembers():
                if not member.isfile():
                    raise TransitionError(f"rollback_archive_nonfile_member:{member.name}")
                name = safe_member(member.name)
                if name in seen or name not in archived_expected:
                    raise TransitionError(f"rollback_archive_unexpected_member:{name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise TransitionError(f"rollback_archive_member_unreadable:{name}")
                raw = stream.read()
                digest, size = archived_expected[name]
                if len(raw) != size or sha256(raw) != digest:
                    raise TransitionError(f"rollback_archive_member_hash_mismatch:{name}")
                seen.add(name)
                payloads[name.removeprefix("local-coding-worker/")] = (raw, stat.S_IMODE(member.mode))
            if seen != set(archived_expected):
                missing = sorted(set(archived_expected) - seen)
                raise TransitionError(f"rollback_archive_member_missing:{missing[:3]}")
    except (OSError, tarfile.TarError) as error:
        raise TransitionError("rollback_archive_unreadable") from error
    return payloads


def validate_candidate(bundle: Bundle) -> dict[str, tuple[bytes, int]]:
    mapping = bundle.mapping
    add = [safe_member(str(value)) for value in mapping.get("add", [])]
    replace = [safe_member(str(value)) for value in mapping.get("replace", [])]
    remove = [safe_member(str(value)) for value in mapping.get("remove", [])]
    if len(set(add + replace + remove)) != len(add + replace + remove):
        raise TransitionError("transition_operation_duplicate")
    source_hashes = mapping.get("source_hashes")
    if not isinstance(source_hashes, dict) or set(source_hashes) != set(replace + remove):
        raise TransitionError("transition_source_operation_coverage_mismatch")
    candidate_hashes = mapping.get("candidate_hashes")
    candidate_modes = mapping.get("candidate_modes")
    if not isinstance(candidate_hashes, dict) or not isinstance(candidate_modes, dict):
        raise TransitionError("transition_candidate_identity_missing")
    expected_candidate = set(add + replace)
    if set(candidate_hashes) != expected_candidate or set(candidate_modes) != expected_candidate:
        raise TransitionError("transition_candidate_operation_coverage_mismatch")
    actual_candidate = {
        path.relative_to(STAGE_ROOT / "runtime").as_posix()
        for path in bundle.candidate_root.rglob("*") if path.is_file()
    }
    if any(path.is_symlink() for path in bundle.candidate_root.rglob("*")):
        raise TransitionError("candidate_symlink_rejected")
    if actual_candidate != expected_candidate:
        raise TransitionError("candidate_file_set_mismatch")
    result: dict[str, tuple[bytes, int]] = {}
    for rel in sorted(expected_candidate):
        safe_member(rel)
        path = STAGE_ROOT / "runtime" / rel
        raw = path.read_bytes()
        if sha256(raw) != candidate_hashes[rel]:
            raise TransitionError(f"candidate_hash_mismatch:{rel}")
        mode = int(str(candidate_modes[rel]), 8)
        if stat.S_IMODE(path.stat().st_mode) != mode:
            raise TransitionError(f"candidate_mode_mismatch:{rel}")
        if rel.endswith(".py"):
            compile(raw, str(path), "exec", dont_inherit=True)
        result[rel.removeprefix("local-coding-worker/")] = (raw, mode)
    return result


def verify_authority_exclusions(bundle: Bundle) -> None:
    inventory = bundle.inventory
    excluded = inventory.get("exclusions")
    mapping = bundle.mapping.get("independent_authorities_preserved")
    if not isinstance(excluded, list) or not isinstance(mapping, list):
        raise TransitionError("independent_authority_exclusions_missing")
    inventory_by_id = {item.get("id"): item for item in excluded if isinstance(item, dict)}
    operations = list(bundle.mapping.get("add", [])) + list(bundle.mapping.get("replace", [])) + list(bundle.mapping.get("remove", []))
    for item in mapping:
        authority_id = item.get("id")
        expected = inventory_by_id.get(authority_id)
        if expected is None:
            raise TransitionError(f"authority_not_in_source_inventory:{authority_id}")
        expected_raw = Path(str(bundle.mapping["source_root"])) / str(expected["path"])
        staged_raw = Path(str(item.get("supplier_path", "")))
        if expected_raw.is_symlink() or staged_raw.is_symlink():
            raise TransitionError(f"independent_authority_symlink_rejected:{authority_id}")
        expected_root = expected_raw.resolve(strict=True)
        staged_root = staged_raw.resolve(strict=True)
        if staged_root != expected_root or not staged_root.is_dir():
            raise TransitionError(f"independent_authority_path_invalid:{authority_id}")
        prefix = str(expected["path"]).rstrip("/") + "/"
        if any(str(operation).startswith(prefix) for operation in operations):
            raise TransitionError(f"independent_authority_in_transition_scope:{authority_id}")
    if {item.get("id") for item in mapping} != {"todo-orchestrator", "cuda", "cpp-context-compiler"}:
        raise TransitionError("independent_authority_exclusion_set_invalid")


def verify_source_preconditions(bundle: Bundle) -> None:
    mapping = bundle.mapping
    source_hashes = mapping["source_hashes"]
    source_modes = mapping.get("source_modes")
    if not isinstance(source_modes, dict) or set(source_modes) != set(source_hashes):
        raise TransitionError("source_modes_missing_or_incomplete")
    for rel, expected in source_hashes.items():
        safe_member(rel)
        path = reject_symlink_components(bundle.source_root, rel)
        if not path.is_file():
            raise TransitionError(f"source_operation_path_invalid:{rel}")
        raw = path.read_bytes()
        if sha256(raw) != expected:
            raise TransitionError(f"source_operation_hash_changed:{rel}")
        if stat.S_IMODE(path.stat().st_mode) != int(str(source_modes[rel]), 8):
            raise TransitionError(f"source_operation_mode_changed:{rel}")
    for rel in mapping.get("replace", []):
        path = bundle.source_root / safe_member(str(rel))
        if not path.is_file():
            raise TransitionError(f"replace_target_missing:{rel}")
    for rel in mapping.get("remove", []):
        path = bundle.source_root / safe_member(str(rel))
        if not path.is_file():
            raise TransitionError(f"remove_target_missing:{rel}")
    for rel in mapping.get("add", []):
        path = bundle.source_root / safe_member(str(rel))
        if path.exists() or path.is_symlink():
            raise TransitionError(f"add_target_already_exists:{rel}")
        if not path.parent.is_dir() or path.parent.is_symlink():
            raise TransitionError(f"add_parent_invalid:{rel}")
    verify_authority_exclusions(bundle)


def receiver_manifest_check(root_value: str) -> tuple[str, int]:
    root = Path(root_value).resolve(strict=True)
    manifest_path = root / "receiver-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise TransitionError("current_receiver_manifest_missing")
    raw = manifest_path.read_bytes()
    manifest = json.loads(raw)
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
        raise TransitionError("current_receiver_manifest_invalid")
    checked = 0
    for rel, expected in manifest["files"].items():
        safe_member(rel)
        path = root / rel
        if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()) != expected:
            raise TransitionError(f"current_receiver_source_mismatch:{rel}")
        checked += 1
    found = {path.relative_to(root).as_posix() for path in root.rglob("*")
             if path.is_file() and path.name != "receiver-manifest.json" and ".pyc" not in path.suffixes}
    if found != set(manifest["files"]):
        raise TransitionError("current_receiver_file_set_mismatch")
    return sha256(raw), checked
