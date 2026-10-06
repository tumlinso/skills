"""Inert explicit operator for SK-PA1-RETIRE. This file performs no work on import."""
from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

from transition_common import (
    MAP_PATH, STAGE_ROOT, TransitionError, archive_files, load_bundle,
    receiver_manifest_check, reject_symlink_components, sha256, validate_candidate,
    verify_source_preconditions,
)


def _atomic_write(target: Path, raw: bytes, mode: int) -> None:
    fd, name = tempfile.mkstemp(prefix=f'.{target.name}.pa1-', dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, target)
    except BaseException:
        # Remove only this process's exact temporary path.
        temporary.unlink(missing_ok=True)
        raise


def _candidate_namespace_check(bundle, pc_repo: Path) -> None:
    candidate_root = STAGE_ROOT / 'runtime' / 'local-coding-worker'
    env = dict(os.environ)
    env.pop("PROJECT_CONTROL_RELEASE_MANIFEST", None)
    env.pop("PROJECT_CONTROL_RELEASE_DIGEST", None)
    old = env.get('PYTHONPATH', '')
    env['PYTHONPATH'] = os.pathsep.join(x for x in (str(pc_repo / 'src'), str(candidate_root), old) if x)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    code = '''import importlib,sys\nfrom pathlib import Path\nfrom project_control.runtime_binding import bind_local_runtime, local_runtime_identity\nmodule = importlib.import_module("local_worker")\nidentity = bind_local_runtime()\ncurrent = local_runtime_identity()\nassert module is sys.modules["local_worker"]\nassert identity.fingerprint == current.fingerprint\nassert Path(module.__file__).resolve() == identity.package_root / "__init__.py"\nprint(identity.manifest_sha256, identity.file_count)\n'''
    result = subprocess.run([sys.executable, '-c', code], cwd=pc_repo, env=env,
                            text=True, capture_output=True, check=False)
    if result.returncode:
        raise TransitionError('candidate_namespace_identity_check_failed:' + (result.stderr.strip()[-1200:] or result.stdout.strip()[-1200:]))


def _run_staged_suite(bundle, pc_repo: Path) -> None:
    suite = STAGE_ROOT / "tests/assistance/test_lcw_transition.py"
    if not suite.is_file() or suite.is_symlink():
        raise TransitionError("staged_transition_test_suite_missing")
    consumers = STAGE_ROOT / "consumers"
    env = dict(os.environ)
    env.pop("PROJECT_CONTROL_RELEASE_MANIFEST", None)
    env.pop("PROJECT_CONTROL_RELEASE_DIGEST", None)
    env.update({
        "PA1_SKILLS_ROOT": str(bundle.source_root),
        "PA1_LEGACY_ROOT": str(bundle.candidate_root),
        "PA1_RECEIVER_ROOT": str(bundle.mapping["receiver"]["root"]),
        "PA1_PC_ROOT": str(pc_repo),
        "PA1_TRANSITION_PATH": str(MAP_PATH),
        "PA1_ROLLBACK_ROOT": str(STAGE_ROOT / "rollback"),
        "PA1_CATALOG_PATH": str(consumers / "integrations/native-skill-catalog.json"),
        "PA1_CATALOG_BASELINE": str(consumers / "provenance/native-skill-catalog.baseline.json"),
        "PA1_RELEASE_CONSUMER": str(consumers / "integrations/as1_release.py"),
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    result = subprocess.run([sys.executable, str(suite)], cwd=pc_repo, env=env,
                            text=True, capture_output=True, check=False, timeout=180)
    if result.returncode:
        detail = (result.stderr.strip() or result.stdout.strip())[-2400:]
        raise TransitionError("staged_transition_test_suite_failed:" + detail)


def _installed_namespace_check(bundle, pc_repo: Path) -> None:
    env = dict(os.environ)
    env.pop("PROJECT_CONTROL_RELEASE_MANIFEST", None)
    env.pop("PROJECT_CONTROL_RELEASE_DIGEST", None)
    old = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = os.pathsep.join(x for x in
        (str(pc_repo / "src"), str(bundle.skill_root), old) if x)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    code = '''import importlib,sys
from pathlib import Path
from project_control.runtime_binding import bind_local_runtime
module=importlib.import_module("local_worker")
identity=bind_local_runtime()
assert module is sys.modules["local_worker"]
assert Path(module.__file__).resolve()==identity.package_root/"__init__.py"
assert identity.root==Path("/home/tumlinson/project-control/src/project_control/local_runtime").resolve()
print(identity.manifest_sha256)
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=pc_repo, env=env,
                            text=True, capture_output=True, check=False, timeout=30)
    if result.returncode:
        raise TransitionError("installed_namespace_identity_check_failed:" +
                              (result.stderr.strip()[-1200:] or result.stdout.strip()[-1200:]))


def _safe_target(root: Path, rel: str) -> Path:
    return reject_symlink_components(root, rel)


def preflight():
    bundle = load_bundle()
    candidate = validate_candidate(bundle)
    rollback_payloads = archive_files(bundle)
    verify_source_preconditions(bundle)
    pc_repo = Path(str(bundle.mapping['receiver']['root'])).resolve(strict=True).parents[2]
    receiver_sha, receiver_count = receiver_manifest_check(str(bundle.mapping['receiver']['root']))
    _candidate_namespace_check(bundle, pc_repo)
    _run_staged_suite(bundle, pc_repo)
    # Repeat all mutable source checks immediately before opening the rollback
    # destination. A single changed path aborts the complete apply batch.
    verify_source_preconditions(bundle)
    rollback_root = bundle.source_root / 'docs' / 'pa1' / 'rollback'
    if rollback_root.exists() or rollback_root.is_symlink():
        raise TransitionError('rollback_destination_already_exists')
    if not rollback_root.parent.is_dir() or rollback_root.parent.is_symlink():
        raise TransitionError('rollback_destination_parent_invalid')
    return bundle, candidate, rollback_payloads, pc_repo, receiver_sha, receiver_count, rollback_root


def apply() -> None:
    bundle, candidate, rollback_payloads, pc_repo, receiver_sha, receiver_count, rollback_root = preflight()

    # Preflight is complete. Install and verify the rollback material first.
    rollback_stage = Path(tempfile.mkdtemp(prefix='.pa1-rollback-stage-', dir=rollback_root.parent))
    rollback_stage.chmod(0o700)
    copies = [
        (bundle.archive_path, rollback_stage / 'local-coding-worker-portable.tar.gz', bundle.mapping['rollback_archive_sha256']),
        (STAGE_ROOT / bundle.mapping['rollback_provenance'], rollback_stage / 'provenance.json', sha256((STAGE_ROOT / bundle.mapping['rollback_provenance']).read_bytes())),
        (MAP_PATH, rollback_stage / 'runtime-transition.json', sha256(MAP_PATH.read_bytes())),
    ]
    for source, target, expected in copies:
        raw = source.read_bytes()
        if sha256(raw) != expected:
            raise TransitionError(f'rollback_copy_source_changed:{source.name}')
        _atomic_write(target, raw, 0o600)
        if sha256(target.read_bytes()) != expected:
            raise TransitionError(f'rollback_copy_verification_failed:{target.name}')
    if set(archive_files(bundle)) != set(rollback_payloads):
        raise TransitionError('rollback_archive_revalidation_failed')
    os.replace(rollback_stage, rollback_root)

    # Forward the package namespace first so imports immediately route through
    # the strict receiver binder. Then replace non-code entrypoints and remove
    # only explicitly hashed supplier modules.
    operations = list(bundle.mapping['add']) + list(bundle.mapping['replace'])
    operations.sort(key=lambda rel: (0 if rel.endswith('/local_worker/__init__.py') else 1, rel))
    for rel in operations:
        relative = rel.removeprefix('local-coding-worker/')
        target = _safe_target(bundle.skill_root, relative)
        staged_raw, mode = candidate[relative]
        if rel in bundle.mapping['add']:
            if target.exists() or target.is_symlink():
                raise TransitionError(f'add_target_changed_after_preflight:{rel}')
        else:
            expected = bundle.mapping['source_hashes'][rel]
            if not target.is_file() or sha256(target.read_bytes()) != expected:
                raise TransitionError(f'replace_target_changed_after_preflight:{rel}')
        _atomic_write(target, staged_raw, mode)
        if sha256(target.read_bytes()) != bundle.mapping['candidate_hashes'][rel]:
            raise TransitionError(f'candidate_install_verification_failed:{rel}')
    for rel in bundle.mapping['remove']:
        target = _safe_target(bundle.skill_root, rel.removeprefix('local-coding-worker/'))
        expected = bundle.mapping['source_hashes'][rel]
        if not target.is_file() or sha256(target.read_bytes()) != expected:
            raise TransitionError(f'remove_target_changed_after_preflight:{rel}')
        target.unlink()
    _installed_namespace_check(bundle, pc_repo)
    print(f'APPLIED receiver_manifest_sha256={receiver_sha} receiver_files={receiver_count} '
          f'rollback={rollback_root} operations={len(operations) + len(bundle.mapping["remove"])}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['preflight', 'apply'],
                        help='preflight is read-only; apply performs the exact mapped transition')
    args = parser.parse_args()
    try:
        if args.operation == 'preflight':
            bundle, candidate, rollback_payloads, _, receiver_sha, receiver_count, rollback_root = preflight()
            print(f'PREFLIGHT_OK receiver_manifest_sha256={receiver_sha} receiver_files={receiver_count} '
                  f'candidate_files={len(candidate)} rollback_files={len(rollback_payloads)} '
                  f'rollback_destination={rollback_root} no_source_mutation=true')
        else:
            apply()
    except (TransitionError, OSError, ValueError, KeyError) as error:
        print(f'PA1 transition refused before/during apply: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
