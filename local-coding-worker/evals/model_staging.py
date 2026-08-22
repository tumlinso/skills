#!/usr/bin/env python3
"""Verify cold model assets and stage one candidate to SSD for a bounded command."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


MANIFEST_NAME = "asset-manifest.json"
RAM_FILESYSTEMS = {"tmpfs", "ramfs"}
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class StagingError(RuntimeError):
    pass


class InsufficientStagingSpace(StagingError):
    def __init__(self, *, required_bytes: int, available_bytes: int) -> None:
        self.required_bytes = required_bytes
        self.available_bytes = available_bytes
        self.additional_bytes_required = max(required_bytes - available_bytes, 0)
        super().__init__(
            "insufficient SSD staging space: "
            f"required={required_bytes} available={available_bytes} "
            f"additional_required={self.additional_bytes_required}"
        )


@dataclass(frozen=True)
class StoragePolicy:
    canonical_root: Path
    staging_root: Path
    minimum_headroom_bytes: int

    @classmethod
    def from_mapping(cls, value: dict[str, Any]) -> "StoragePolicy":
        required = {"canonical_root", "staging_root", "minimum_headroom_bytes"}
        missing = required - set(value)
        if missing:
            raise StagingError(f"storage policy is missing fields: {sorted(missing)}")
        headroom = value["minimum_headroom_bytes"]
        if isinstance(headroom, bool) or not isinstance(headroom, int) or headroom < 0:
            raise StagingError("minimum_headroom_bytes must be a non-negative integer")
        canonical = Path(str(value["canonical_root"])).expanduser().resolve()
        staging = Path(str(value["staging_root"])).expanduser().resolve()
        if canonical == staging or canonical in staging.parents or staging in canonical.parents:
            raise StagingError("canonical_root and staging_root must be independent trees")
        return cls(canonical_root=canonical, staging_root=staging, minimum_headroom_bytes=headroom)


def load_policy(path: Path) -> StoragePolicy:
    with path.open("rb") as handle:
        document = tomllib.load(handle)
    storage = document.get("storage")
    if not isinstance(storage, dict):
        raise StagingError("configuration requires a [storage] table")
    return StoragePolicy.from_mapping(storage)


def _inside(root: Path, candidate: Path) -> bool:
    return candidate == root or root in candidate.parents


def _candidate_dir(policy: StoragePolicy, candidate_id: str) -> Path:
    if not IDENTIFIER.fullmatch(candidate_id):
        raise StagingError("candidate id must contain only lowercase letters, digits, dot, underscore, or dash")
    candidate = (policy.canonical_root / candidate_id).resolve()
    if not _inside(policy.canonical_root, candidate):
        raise StagingError("candidate path escapes canonical_root")
    return candidate


def _filesystem_type(path: Path) -> str | None:
    probe = path.resolve()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    best: tuple[int, str] | None = None
    try:
        lines = Path("/proc/self/mountinfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        left, separator, right = line.partition(" - ")
        if not separator:
            continue
        fields = left.split()
        after = right.split()
        if len(fields) < 5 or not after:
            continue
        mountpoint = Path(fields[4].replace("\\040", " ")).resolve()
        if _inside(mountpoint, probe):
            rank = len(mountpoint.parts)
            if best is None or rank > best[0]:
                best = (rank, after[0])
    return best[1] if best else None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_asset_manifest(candidate_dir: Path, candidate_id: str) -> dict[str, Any]:
    manifest_path = candidate_dir / MANIFEST_NAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StagingError(f"invalid or missing canonical manifest: {manifest_path}") from error
    if manifest.get("format") != "CORE4-MODEL-ASSET/1" or manifest.get("candidate_id") != candidate_id:
        raise StagingError("canonical manifest format or candidate_id is invalid")
    source = manifest.get("source")
    if not isinstance(source, dict) or not source.get("repository") or not source.get("revision"):
        raise StagingError("canonical manifest requires source repository and revision")
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        raise StagingError("canonical manifest requires at least one file")
    for record in files:
        if not isinstance(record, dict) or not isinstance(record.get("path"), str):
            raise StagingError("canonical manifest file records require a path")
        relative = Path(record["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise StagingError("canonical manifest file path must be relative and contained")
        if not SHA256.fullmatch(str(record.get("sha256", ""))):
            raise StagingError("canonical manifest file record requires lowercase SHA256")
        size = record.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise StagingError("canonical manifest file record requires a non-negative byte count")
    return manifest


def verify_candidate(policy: StoragePolicy, candidate_id: str) -> dict[str, Any]:
    candidate_dir = _candidate_dir(policy, candidate_id)
    if not candidate_dir.is_dir():
        raise StagingError(f"canonical candidate directory does not exist: {candidate_dir}")
    manifest = _load_asset_manifest(candidate_dir, candidate_id)
    verified = []
    payload_bytes = 0
    for record in manifest["files"]:
        source = (candidate_dir / record["path"]).resolve()
        if not _inside(candidate_dir, source) or source.is_symlink() or not source.is_file():
            raise StagingError(f"canonical model file is missing or unsafe: {record['path']}")
        actual_size = source.stat().st_size
        if actual_size != record["bytes"]:
            raise StagingError(f"canonical model size mismatch: {record['path']}")
        actual_hash = _sha256(source)
        if actual_hash != record["sha256"]:
            raise StagingError(f"canonical model checksum mismatch: {record['path']}")
        payload_bytes += actual_size
        verified.append({"path": record["path"], "bytes": actual_size, "sha256": actual_hash})
    policy.staging_root.mkdir(parents=True, exist_ok=True)
    filesystem_type = _filesystem_type(policy.staging_root)
    if filesystem_type in RAM_FILESYSTEMS:
        raise StagingError(f"RAM filesystem is not allowed for primary staging: {filesystem_type}")
    available = shutil.disk_usage(policy.staging_root).free
    required = payload_bytes + policy.minimum_headroom_bytes
    if available < required:
        raise InsufficientStagingSpace(required_bytes=required, available_bytes=available)
    return {
        "candidate_id": candidate_id,
        "canonical_dir": str(candidate_dir),
        "staging_root": str(policy.staging_root),
        "staging_filesystem": filesystem_type,
        "payload_bytes": payload_bytes,
        "minimum_headroom_bytes": policy.minimum_headroom_bytes,
        "required_bytes": required,
        "available_bytes": available,
        "source": manifest["source"],
        "files": verified,
    }


def _remove_tree(path: Path, staging_root: Path) -> None:
    resolved = path.resolve()
    if resolved == staging_root or not _inside(staging_root, resolved):
        raise StagingError("refusing cleanup outside candidate-specific staging path")
    if resolved.exists():
        shutil.rmtree(resolved)


@contextlib.contextmanager
def staged_candidate(policy: StoragePolicy, candidate_id: str) -> Iterator[dict[str, Any]]:
    verification = verify_candidate(policy, candidate_id)
    canonical = Path(verification["canonical_dir"])
    final = (policy.staging_root / candidate_id).resolve()
    if final.exists():
        raise StagingError(f"candidate staging path already exists; clean it explicitly: {final}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{candidate_id}-partial-", dir=policy.staging_root))
    try:
        for record in verification["files"]:
            source = canonical / record["path"]
            destination = temporary / record["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if destination.stat().st_size != record["bytes"] or _sha256(destination) != record["sha256"]:
                raise StagingError(f"staged model verification failed: {record['path']}")
        shutil.copy2(canonical / MANIFEST_NAME, temporary / MANIFEST_NAME)
        os.replace(temporary, final)
        temporary = final
        yield {**verification, "staged_dir": str(final), "manifest_path": str(final / MANIFEST_NAME)}
    finally:
        _remove_tree(temporary, policy.staging_root)


def run_staged(policy: StoragePolicy, candidate_id: str, command: list[str]) -> int:
    if not command:
        raise StagingError("run requires a command after --")
    with staged_candidate(policy, candidate_id) as staged:
        environment = dict(os.environ)
        environment["CORE4_STAGED_MODEL_DIR"] = staged["staged_dir"]
        process = subprocess.Popen(command, env=environment)
        try:
            return process.wait()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise


@contextlib.contextmanager
def _interrupts_raise() -> Iterator[None]:
    previous: dict[int, Any] = {}

    def interrupt(signum, _frame):
        raise InterruptedError(f"received signal {signum}")

    for signum in (signal.SIGTERM, signal.SIGHUP):
        previous[signum] = signal.signal(signum, interrupt)
    try:
        yield
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    for name in ("verify", "run"):
        action = actions.add_parser(name)
        action.add_argument("--config", required=True)
        action.add_argument("--candidate", required=True)
        if name == "run":
            action.add_argument("command", nargs=argparse.REMAINDER)
    cleanup = actions.add_parser("cleanup")
    cleanup.add_argument("--config", required=True)
    cleanup.add_argument("--candidate", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    policy = load_policy(Path(args.config))
    if args.action == "verify":
        print(json.dumps(verify_candidate(policy, args.candidate), indent=2))
        return 0
    if args.action == "cleanup":
        target = (policy.staging_root / args.candidate).resolve()
        _candidate_dir(policy, args.candidate)
        _remove_tree(target, policy.staging_root)
        print(json.dumps({"candidate_id": args.candidate, "cleaned": True, "path": str(target)}))
        return 0
    command = list(args.command)
    if command and command[0] == "--":
        command.pop(0)
    with _interrupts_raise():
        return run_staged(policy, args.candidate, command)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except StagingError as error:
        print(json.dumps({"ok": False, "error": str(error)}), file=sys.stderr)
        raise SystemExit(2)
