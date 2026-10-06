"""Inert guarded rollback operator for an applied SK-PA1-RETIRE transition."""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from transition_common import (
    TransitionError, archive_files, read_json, reject_symlink_components,
    safe_member, sha256,
)


def _atomic_write(target: Path, raw: bytes, mode: int) -> None:
    fd, name = tempfile.mkstemp(prefix=f'.{target.name}.pa1-restore-', dir=target.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, target)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def restore() -> None:
    parser_map = Path('/home/tumlinson/.agents/skills/docs/pa1/rollback/runtime-transition.json')
    map_value = read_json(parser_map)
    if map_value.get('format') != 'pa1-skills-runtime-transition-candidate/1':
        raise TransitionError('transition_map_format_invalid')
    source_root = Path(map_value['source_root']).resolve(strict=True)
    skill_root = source_root / 'local-coding-worker'
    rollback_root = source_root / 'docs' / 'pa1' / 'rollback'
    provenance_path = rollback_root / 'provenance.json'
    archive_path = rollback_root / 'local-coding-worker-portable.tar.gz'
    provenance = read_json(provenance_path)
    if provenance.get('format') != 'pa1-skills-runtime-rollback/1':
        raise TransitionError('rollback_provenance_format_invalid')
    if sha256(archive_path.read_bytes()) != map_value.get('rollback_archive_sha256'):
        raise TransitionError('rollback_archive_hash_mismatch')
    # Reuse manifest validation against the retained transition map and archive.
    from transition_common import Bundle
    operator_root = Path(__file__).resolve().parent
    inventory_path = operator_root / 'source-inventory.json'
    import json
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    bundle = Bundle(map_value, provenance, inventory, source_root,
                    skill_root, operator_root / 'runtime' / 'local-coding-worker', archive_path)
    originals = archive_files(bundle)
    add = [safe_member(str(x)) for x in map_value['add']]
    replace = [safe_member(str(x)) for x in map_value['replace']]
    remove = [safe_member(str(x)) for x in map_value['remove']]
    candidates = map_value['candidate_hashes']
    modes = map_value['source_modes']
    # Preflight every operated path. Unknown changes stop the whole restoration.
    for rel in replace:
        path = reject_symlink_components(skill_root, rel.removeprefix('local-coding-worker/'))
        if not path.is_file() or sha256(path.read_bytes()) != candidates[rel]:
            raise TransitionError(f'restore_candidate_changed:{rel}')
    for rel in remove:
        path = reject_symlink_components(skill_root, rel.removeprefix('local-coding-worker/'))
        if path.exists():
            raise TransitionError(f'restore_removed_path_reappeared:{rel}')
    for rel in add:
        path = reject_symlink_components(skill_root, rel.removeprefix('local-coding-worker/'))
        if not path.is_file() or sha256(path.read_bytes()) != candidates[rel]:
            raise TransitionError(f'restore_added_path_changed:{rel}')
    if set(replace + remove) != set(map_value['source_hashes']):
        raise TransitionError('restore_operation_coverage_mismatch')
    operation_paths = set(map_value['source_hashes'])
    if {f'local-coding-worker/{relative}' for relative in originals} & operation_paths != operation_paths:
        raise TransitionError('rollback_archive_does_not_cover_runtime_operations')

    # Restore original paths atomically, then remove only the exact added package shim.
    for rel in sorted(replace + remove):
        relative = rel.removeprefix('local-coding-worker/')
        target = reject_symlink_components(skill_root, relative)
        if target.exists() and not target.is_file():
            raise TransitionError(f'restore_target_path_invalid:{rel}')
        if not target.parent.is_dir():
            raise TransitionError(f'restore_target_parent_missing:{rel}')
        raw, _archive_mode = originals[relative]
        expected = map_value['source_hashes'][rel]
        if sha256(raw) != expected:
            raise TransitionError(f'restore_original_hash_mismatch:{rel}')
        mode = int(str(modes[rel]), 8)
        _atomic_write(target, raw, mode)
    for rel in add:
        target = reject_symlink_components(skill_root, rel.removeprefix('local-coding-worker/'))
        if sha256(target.read_bytes()) != candidates[rel]:
            raise TransitionError(f'restore_added_path_changed_during_restore:{rel}')
        target.unlink()
    print(f'RESTORED source_files={len(replace) + len(remove)} added_shims_removed={len(add)}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['restore'], help='only explicit restore is supported')
    parser.parse_args()
    try:
        restore()
    except (TransitionError, OSError, ValueError, KeyError) as error:
        print(f'PA1 rollback refused before/during restore: {error}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
