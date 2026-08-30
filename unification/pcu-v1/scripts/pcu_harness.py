#!/usr/bin/env python3
"""Deterministic, fail-closed verification primitives for PCU-V1.

This module never selects a live repository, registration, service, or virtual
environment.  Callers must provide every path and command explicitly.  The
default CLI surface is read-only; commands that create candidates or rehearsal
clones require a new, caller-owned destination.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
from typing import Any, Callable, Iterable, Mapping, Sequence


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REMOTE_RE = re.compile(r"^(?:https?://|ssh://|git://|git@)[^\s]+$")
SECRET_KEY_RE = re.compile(r"(?:token|secret|password|credential|capability|approval)", re.I)


class HarnessError(RuntimeError):
    """A deterministic safety or contract check failed."""


def _run(
    argv: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if not argv or any(not isinstance(item, str) or not item for item in argv):
        raise HarnessError("commands must be non-empty argv arrays")
    result = subprocess.run(
        list(argv),
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env else None,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and result.returncode:
        rendered = " ".join(shlex.quote(item) for item in argv)
        raise HarnessError(f"command failed ({result.returncode}): {rendered}\n{result.stderr.strip()}")
    return result


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def redact(value: Any) -> Any:
    """Remove secret-bearing mapping values before evidence serialization."""
    if isinstance(value, Mapping):
        return {
            str(key): ("<redacted>" if SECRET_KEY_RE.search(str(key)) else redact(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    return value


def write_evidence(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json(redact(value)) + b"\n")


def _git(repo: Path, *args: str, check: bool = True) -> str:
    return _run(("git", *args), cwd=repo, check=check).stdout.strip()


def canonical_root(repo: Path) -> Path:
    return Path(_git(repo, "rev-parse", "--show-toplevel")).resolve()


def git_common_dir(repo: Path) -> Path:
    raw = _git(repo, "rev-parse", "--git-common-dir")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = canonical_root(repo) / candidate
    return candidate.resolve()


def git_tree_digest(repo: Path, ref: str) -> str:
    """Hash the canonical NUL-delimited tree listing for ``ref``."""
    result = subprocess.run(
        ["git", "ls-tree", "-rz", "--full-tree", ref],
        cwd=str(repo),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode:
        raise HarnessError(result.stderr.decode("utf-8", "replace").strip())
    return sha256_bytes(result.stdout)


def _working_tree_bytes(repo: Path) -> bytes:
    tracked = subprocess.run(
        ["git", "diff", "--binary", "HEAD", "--"],
        cwd=str(repo),
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    untracked_raw = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=str(repo),
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    payload = bytearray(tracked)
    for raw_name in sorted(filter(None, untracked_raw.split(b"\0"))):
        name = raw_name.decode("utf-8", "surrogateescape")
        path = repo / name
        payload.extend(b"\0UNTRACKED\0" + raw_name + b"\0")
        if path.is_file() and not path.is_symlink():
            payload.extend(path.read_bytes())
        elif path.is_symlink():
            payload.extend(os.readlink(path).encode("utf-8", "surrogateescape"))
    return bytes(payload)


@dataclasses.dataclass(frozen=True)
class RepositorySentinel:
    root: str
    head: str
    common_dir: str
    worktree_digest: str
    immutable_files: Mapping[str, str]
    immutable_values: Mapping[str, Any]

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _json_field(path: Path, dotted_field: str) -> Any:
    value: Any = json.loads(path.read_text(encoding="utf-8"))
    for part in dotted_field.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise HarnessError(f"missing immutable JSON field {path}:{dotted_field}")
        value = value[part]
    return value


def repository_sentinel(
    repo: Path,
    immutable_paths: Iterable[str] = (),
    immutable_json_fields: Mapping[str, Sequence[str]] | None = None,
) -> RepositorySentinel:
    root = canonical_root(repo)
    file_hashes: dict[str, str] = {}
    for relative in sorted(set(immutable_paths)):
        candidate = root / relative
        file_hashes[relative] = sha256_file(candidate) if candidate.is_file() else "<missing>"
    field_values: dict[str, Any] = {}
    for relative, fields in sorted((immutable_json_fields or {}).items()):
        candidate = root / relative
        for field in sorted(set(fields)):
            field_values[f"{relative}:{field}"] = _json_field(candidate, field)
    return RepositorySentinel(
        root=str(root),
        head=_git(root, "rev-parse", "HEAD"),
        common_dir=str(git_common_dir(root)),
        worktree_digest=sha256_bytes(_working_tree_bytes(root)),
        immutable_files=file_hashes,
        immutable_values=field_values,
    )


def assert_unchanged(before: RepositorySentinel, after: RepositorySentinel) -> None:
    if before != after:
        raise HarnessError("source repository sentinel changed during isolated operation")


def assert_authority_unchanged(before: RepositorySentinel, after: RepositorySentinel) -> None:
    """Compare commit and selected authority data while allowing owned file edits."""
    if (
        before.head != after.head
        or before.immutable_files != after.immutable_files
        or before.immutable_values != after.immutable_values
    ):
        raise HarnessError("rehearsal changed immutable Git or Todo authority state")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def require_new_independent_destination(source: Path, destination: Path) -> None:
    source_root = canonical_root(source)
    destination = destination.resolve()
    if destination.exists():
        raise HarnessError("destination already exists")
    if _is_relative_to(destination, source_root) or _is_relative_to(source_root, destination):
        raise HarnessError("destination must be outside the source repository")
    # A path beneath the source Git common directory could share authority even
    # when it is outside the visible worktree.
    if _is_relative_to(destination, git_common_dir(source_root)):
        raise HarnessError("destination must be outside the source Git common directory")


def clone_independent(
    source: Path,
    destination: Path,
    *,
    recursive: bool = False,
    git_config: Mapping[str, str] | None = None,
) -> Path:
    source_root = canonical_root(source)
    require_new_independent_destination(source_root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    argv = ["git", "-c", "protocol.file.allow=always"]
    for key, value in sorted((git_config or {}).items()):
        argv.extend(("-c", f"{key}={value}"))
    argv.extend(("clone", "--no-local"))
    if recursive:
        argv.append("--recurse-submodules")
    argv.extend((str(source_root), str(destination)))
    _run(argv)
    clone_root = canonical_root(destination)
    if git_common_dir(clone_root) == git_common_dir(source_root):
        raise HarnessError("clone shares the source Git common directory")
    return clone_root


def _validate_schema(value: Any, schema: Mapping[str, Any], location: str = "$") -> None:
    expected = schema.get("type")
    type_ok = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
    }
    if expected in type_ok and not type_ok[expected]:
        raise HarnessError(f"{location}: expected {expected}")
    if "const" in schema and value != schema["const"]:
        raise HarnessError(f"{location}: value does not match const")
    if isinstance(value, str):
        if len(value) < int(schema.get("minLength", 0)):
            raise HarnessError(f"{location}: string is too short")
        if "pattern" in schema and not re.fullmatch(str(schema["pattern"]), value):
            raise HarnessError(f"{location}: string does not match pattern")
        if schema.get("format") == "date-time" and not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value
        ):
            raise HarnessError(f"{location}: invalid date-time")
    if isinstance(value, int) and "minimum" in schema and value < int(schema["minimum"]):
        raise HarnessError(f"{location}: integer below minimum")
    if isinstance(value, list):
        if len(value) < int(schema.get("minItems", 0)) or len(value) > int(schema.get("maxItems", len(value))):
            raise HarnessError(f"{location}: invalid item count")
        if schema.get("uniqueItems") and len({_canonical_json(item) for item in value}) != len(value):
            raise HarnessError(f"{location}: items are not unique")
        if isinstance(schema.get("items"), Mapping):
            for index, item in enumerate(value):
                _validate_schema(item, schema["items"], f"{location}[{index}]")
        if isinstance(schema.get("contains"), Mapping):
            if not any(_schema_matches(item, schema["contains"]) for item in value):
                raise HarnessError(f"{location}: contains constraint failed")
    if isinstance(value, dict):
        required = set(schema.get("required", []))
        missing = sorted(required - set(value))
        if missing:
            raise HarnessError(f"{location}: missing required properties {missing}")
        if len(value) < int(schema.get("minProperties", 0)):
            raise HarnessError(f"{location}: too few properties")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_schema = properties.get(key)
            if child_schema is None:
                if additional is False:
                    raise HarnessError(f"{location}: unexpected property {key}")
                if isinstance(additional, Mapping):
                    child_schema = additional
            if isinstance(child_schema, Mapping):
                _validate_schema(item, child_schema, f"{location}.{key}")


def _schema_matches(value: Any, schema: Mapping[str, Any]) -> bool:
    try:
        _validate_schema(value, schema)
    except HarnessError:
        return False
    return True


def validate_release_manifest(manifest_path: Path, schema_path: Path) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    _validate_schema(manifest, schema)
    if set(manifest["observer_tool_names"]) != set(manifest["observer_schema_hashes"]):
        raise HarnessError("observer schema hash keys do not exactly match observer tools")
    if set(manifest["codex_tool_names"]) != set(manifest["codex_schema_hashes"]):
        raise HarnessError("codex schema hash keys do not exactly match codex tools")
    if "coding-workflow" not in manifest["compatibility_aliases"]:
        raise HarnessError("release manifest must retain the coding-workflow compatibility alias")
    return manifest


def validate_release_source(manifest: Mapping[str, Any], repo: Path, release_commit: str) -> dict[str, str]:
    root = canonical_root(repo)
    release = _git(root, "rev-parse", f"{release_commit}^{{commit}}")
    parent = _git(root, "rev-parse", f"{release}^")
    if manifest["source_parent_commit"] != parent:
        raise HarnessError("manifest source_parent_commit is not the release parent")
    actual_tree_hash = git_tree_digest(root, parent)
    if manifest["source_tree_hash"] != actual_tree_hash:
        raise HarnessError("manifest source_tree_hash does not match the parent source tree")
    return {"release_commit": release, "source_parent_commit": parent, "source_tree_hash": actual_tree_hash}


def validate_release_lock(lock_path: Path, manifest_path: Path, repo: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    required = {"schema_version", "project_control_commit", "manifest_sha256", "source_tree_hash", "remote_url"}
    if set(lock) != required or lock["schema_version"] != 1:
        raise HarnessError("release lock has an unsupported shape")
    if not COMMIT_RE.fullmatch(str(lock["project_control_commit"])):
        raise HarnessError("release lock commit is invalid")
    if not SHA256_RE.fullmatch(str(lock["manifest_sha256"])):
        raise HarnessError("release lock manifest digest is invalid")
    if lock["manifest_sha256"] != sha256_file(manifest_path):
        raise HarnessError("release lock manifest digest mismatch")
    if not REMOTE_RE.fullmatch(str(lock["remote_url"])):
        raise HarnessError("release lock must use a legitimate non-local remote URL")
    if _git(repo, "rev-parse", "HEAD") != lock["project_control_commit"]:
        raise HarnessError("release lock commit does not match checked out Project Control")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if lock["source_tree_hash"] != manifest["source_tree_hash"]:
        raise HarnessError("release lock source tree hash mismatch")
    return lock


def verify_submodule_pin(parent: Path, relative_path: str, expected_commit: str) -> dict[str, str]:
    parent = canonical_root(parent)
    if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
        raise HarnessError("submodule path must be relative and contained")
    stage = _git(parent, "ls-files", "-s", "--", relative_path)
    fields = stage.split()
    if len(fields) < 4 or fields[0] != "160000" or fields[1] != expected_commit:
        raise HarnessError("parent gitlink does not match the expected commit")
    submodule = parent / relative_path
    if _git(submodule, "rev-parse", "HEAD") != expected_commit:
        raise HarnessError("submodule worktree does not match the expected commit")
    url = _git(parent, "config", "-f", ".gitmodules", "--get", f"submodule.{relative_path}.url")
    if not REMOTE_RE.fullmatch(url):
        raise HarnessError("final submodule URL is local-only or unsupported")
    return {"path": relative_path, "commit": expected_commit, "url": url}


@dataclasses.dataclass(frozen=True)
class CandidatePlan:
    destination: str
    commands: tuple[tuple[str, ...], ...]
    rollback_state: str

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def candidate_plan(
    *,
    skills_root: Path,
    project_control_root: Path,
    destination: Path,
    rollback_state: Path,
    python_executable: str = sys.executable,
) -> CandidatePlan:
    skills_root = canonical_root(skills_root)
    project_control_root = canonical_root(project_control_root)
    destination = destination.resolve()
    if destination.exists():
        raise HarnessError("candidate destination already exists")
    for source in (skills_root, project_control_root):
        if _is_relative_to(destination, source) or _is_relative_to(source, destination):
            raise HarnessError("candidate environment must be isolated from source repositories")
    candidate_python = destination / "bin" / "python"
    commands = (
        (python_executable, "-m", "venv", str(destination)),
        (
            str(candidate_python),
            "-m",
            "pip",
            "install",
            "--no-deps",
            str(skills_root / "todo-orchestrator"),
            str(project_control_root),
        ),
        (str(candidate_python), "-m", "project_control", "--help"),
    )
    return CandidatePlan(str(destination), commands, str(rollback_state.resolve()))


Runner = Callable[[Sequence[str], Path | None], subprocess.CompletedProcess[str]]


def _default_runner(argv: Sequence[str], cwd: Path | None) -> subprocess.CompletedProcess[str]:
    return _run(argv, cwd=cwd)


def atomic_swap(
    *,
    forward_commands: Sequence[Sequence[str]],
    verify_commands: Sequence[Sequence[str]],
    rollback_commands: Sequence[Sequence[str]],
    runner: Runner = _default_runner,
) -> dict[str, Any]:
    """Execute an explicit swap and automatically roll back on any failure."""
    if not forward_commands or not verify_commands or not rollback_commands:
        raise HarnessError("forward, verification, and rollback commands are all required")
    completed: list[list[str]] = []
    try:
        for command in (*forward_commands, *verify_commands):
            runner(tuple(command), None)
            completed.append(list(command))
    except Exception as error:
        rollback_errors: list[str] = []
        for command in rollback_commands:
            try:
                runner(tuple(command), None)
            except Exception as rollback_error:  # pragma: no cover - retained in evidence
                rollback_errors.append(type(rollback_error).__name__)
        raise HarnessError(
            f"atomic swap failed; rollback attempted; rollback_errors={rollback_errors}; cause={type(error).__name__}"
        ) from error
    return {"status": "verified", "commands_completed": len(completed), "rollback_required": False}


@dataclasses.dataclass(frozen=True)
class MigrationRehearsalResult:
    source_unchanged: bool
    independent_common_dir: bool
    dry_run_clean: bool
    apply_changed_paths: tuple[str, ...]
    reapply_idempotent: bool
    remove_restored: bool
    original_ancestry_reachable: bool

    def to_json(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _changed_paths(repo: Path) -> tuple[str, ...]:
    raw = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=str(repo),
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    paths: list[str] = []
    records = [record for record in raw.split(b"\0") if record]
    index = 0
    while index < len(records):
        record = records[index].decode("utf-8", "surrogateescape")
        paths.append(record[3:])
        if record[:2].strip() in {"R", "C"} and index + 1 < len(records):
            index += 1
            paths.append(records[index].decode("utf-8", "surrogateescape"))
        index += 1
    return tuple(sorted(set(paths)))


def rehearse_migration(
    *,
    source: Path,
    destination: Path,
    dry_run_command: Sequence[str],
    apply_command: Sequence[str],
    remove_command: Sequence[str],
    allowed_paths: Iterable[str],
    immutable_paths: Iterable[str] = (),
    immutable_json_fields: Mapping[str, Sequence[str]] | None = None,
) -> MigrationRehearsalResult:
    source_before = repository_sentinel(source, immutable_paths, immutable_json_fields)
    clone = clone_independent(source, destination)
    clone_authority = repository_sentinel(clone, immutable_paths, immutable_json_fields)
    original_head = _git(clone, "rev-parse", "HEAD")
    original_clone_digest = sha256_bytes(_working_tree_bytes(clone))
    _run(tuple(dry_run_command), cwd=clone)
    dry_run_clean = sha256_bytes(_working_tree_bytes(clone)) == original_clone_digest
    if not dry_run_clean:
        raise HarnessError("migration dry-run changed the rehearsal clone")
    _run(tuple(apply_command), cwd=clone)
    assert_authority_unchanged(
        clone_authority,
        repository_sentinel(clone, immutable_paths, immutable_json_fields),
    )
    first_apply_digest = sha256_bytes(_working_tree_bytes(clone))
    changed = _changed_paths(clone)
    unexpected = sorted(set(changed) - set(allowed_paths))
    if unexpected:
        raise HarnessError(f"migration changed paths outside its owned scope: {unexpected}")
    _run(tuple(apply_command), cwd=clone)
    assert_authority_unchanged(
        clone_authority,
        repository_sentinel(clone, immutable_paths, immutable_json_fields),
    )
    reapply_idempotent = sha256_bytes(_working_tree_bytes(clone)) == first_apply_digest
    if not reapply_idempotent:
        raise HarnessError("migration reapply was not idempotent")
    _run(tuple(remove_command), cwd=clone)
    assert_authority_unchanged(
        clone_authority,
        repository_sentinel(clone, immutable_paths, immutable_json_fields),
    )
    remove_restored = sha256_bytes(_working_tree_bytes(clone)) == original_clone_digest
    if not remove_restored:
        raise HarnessError("migration remove did not restore migration-owned fields")
    ancestry = _run(("git", "merge-base", "--is-ancestor", original_head, "HEAD"), cwd=clone, check=False).returncode == 0
    source_after = repository_sentinel(source, immutable_paths, immutable_json_fields)
    assert_unchanged(source_before, source_after)
    return MigrationRehearsalResult(
        source_unchanged=True,
        independent_common_dir=git_common_dir(source) != git_common_dir(clone),
        dry_run_clean=True,
        apply_changed_paths=changed,
        reapply_idempotent=True,
        remove_restored=True,
        original_ancestry_reachable=ancestry,
    )


def _load_commands(path: Path) -> list[list[str]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(
        isinstance(command, list) and command and all(isinstance(item, str) and item for item in command)
        for command in value
    ):
        raise HarnessError("command file must contain an array of non-empty argv arrays")
    return value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    release = sub.add_parser("verify-release")
    release.add_argument("--manifest", type=Path, required=True)
    release.add_argument("--schema", type=Path, required=True)
    release.add_argument("--repo", type=Path, required=True)
    release.add_argument("--release-commit", required=True)

    clone = sub.add_parser("verify-independent-clone")
    clone.add_argument("--source", type=Path, required=True)
    clone.add_argument("--destination", type=Path, required=True)
    clone.add_argument("--recursive", action="store_true")

    candidate = sub.add_parser("candidate-plan")
    candidate.add_argument("--skills-root", type=Path, required=True)
    candidate.add_argument("--project-control-root", type=Path, required=True)
    candidate.add_argument("--destination", type=Path, required=True)
    candidate.add_argument("--rollback-state", type=Path, required=True)

    swap = sub.add_parser("atomic-swap")
    swap.add_argument("--forward", type=Path, required=True)
    swap.add_argument("--verify", type=Path, required=True)
    swap.add_argument("--rollback", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "verify-release":
        manifest = validate_release_manifest(args.manifest, args.schema)
        output = validate_release_source(manifest, args.repo, args.release_commit)
    elif args.command == "verify-independent-clone":
        source = repository_sentinel(args.source)
        target = clone_independent(args.source, args.destination, recursive=args.recursive)
        assert_unchanged(source, repository_sentinel(args.source))
        output = {"status": "independent", "head": _git(target, "rev-parse", "HEAD")}
    elif args.command == "candidate-plan":
        output = candidate_plan(
            skills_root=args.skills_root,
            project_control_root=args.project_control_root,
            destination=args.destination,
            rollback_state=args.rollback_state,
        ).to_json()
    else:
        output = atomic_swap(
            forward_commands=_load_commands(args.forward),
            verify_commands=_load_commands(args.verify),
            rollback_commands=_load_commands(args.rollback),
        )
    print(json.dumps(redact(output), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
