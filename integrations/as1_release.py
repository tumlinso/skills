"""Read-only standalone paired release consumer and post-proof manifest binding.

Binding writes only the explicit Skills release manifest, never runtime or Todo.
Qualification and live effects must already have been executed by their owners.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import hashlib

SKILLS = Path(__file__).resolve().parents[1]
DEFAULT = SKILLS / 'integrations/as1-paired-release.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_bound(reference):
    path = Path(reference['path']).resolve(strict=True)
    assert reference['sha256'] and sha(path) == reference['sha256'], f'Unbound or changed artifact: {path}'
    return path, json.loads(path.read_text())


def passing_cases(report, cases):
    assert report['pytest_exitstatus'] == 0, 'Qualification failed'
    for case in cases:
        rows = report['cases'][case]
        assert rows and all(row['outcome'] == 'passed' for row in rows), case


def validate_identity(release):
    assert release['format'] == 'skills-as1-paired-release/1'
    candidate = Path(release['candidate']['path']).resolve(strict=True)
    manifest = candidate / 'release-manifest.json'
    assert sha(manifest) == release['candidate']['manifest_sha256']
    installed = json.loads(manifest.read_text())
    assert installed['project_control_commit'] == release['pins']['project_control']
    assert installed['todo_commit'] == release['pins']['skills']
    assert Path(installed['skills_root']).resolve() == candidate / 'runtime-skills'
    assert sha(candidate / 'runtime-skills/local-coding-worker/local_worker/observer_runtime.py') == release['pins']['observer_runtime_sha256']
    for relative, expected in installed['frozen_skill_resources'].items():
        resource = (candidate / 'runtime-skills' / relative).resolve(strict=True)
        assert resource.is_relative_to(candidate / 'runtime-skills')
        assert sha(resource) == expected, relative
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=SKILLS).decode().split('\0')
    for entry in filter(None, entries):
        metadata, name = entry.split('\t', 1)
        assert metadata.split()[0] != '160000', f'Skills must be standalone: gitlink {name}'
        path = Path(name)
        if path.suffix == '.py':
            assert not {'project-control', 'project_control'} & set(path.parts), f'Project Control source copy: {name}'
    assert not (SKILLS / 'project-control').exists(), 'Standalone Skills must not contain a second Project Control checkout'
    assert not (SKILLS / 'project_control').exists(), 'Standalone Skills must not contain a Project Control source copy'
    instructions = release['instructions']
    path = (SKILLS / instructions['path']).resolve(strict=True)
    assert path.is_relative_to(SKILLS) and sha(path) == instructions['sha256']
    return candidate


def validate_release(release, *, require_passed=True):
    candidate = validate_identity(release)
    if require_passed:
        assert release['status'] == 'passed', 'Paired release pending actual qualification and live release proof'
    evidence = release['evidence']
    _, qualification = read_bound(evidence['skills_qualification'])
    passing_cases(qualification, {'SQA-01', 'SQA-02', 'SQA-03'})
    proof_path, proof = read_bound(evidence['skills_real_proof'])
    assert proof['format'] == 'as1-paired-realproof/1' and proof['status'] == 'passed'
    identity = proof['source_identity']
    assert Path(identity['candidate_root']).resolve() == candidate
    assert identity['pc_commit'] == release['pins']['project_control']
    assert identity['skills_commit'] == release['pins']['skills']
    assert identity['release_sha256'] == release['candidate']['manifest_sha256']
    assert identity['observer_runtime_sha256'] == release['pins']['observer_runtime_sha256']
    assert proof['artifacts']
    for relative, expected in proof['artifacts'].items():
        path = (proof_path.parent / relative).resolve(strict=True)
        assert path.is_relative_to(proof_path.parent)
        assert sha(path) == expected, relative
    for name in ('scout', 'skill', 'eviction', 'restart', 'checkpoint', 'poll'):
        assert proof['journeys'][name]['status'] == 'passed'
        assert proof['journeys'][name]['artifact'] in proof['artifacts']
    live_path, live = read_bound(evidence['live_release'])
    assert live['format'] == 'pc-as1-live-release/1' and live['status'] == 'passed'
    for key in ('candidate_root', 'pc_commit', 'skills_commit', 'release_sha256'):
        assert live['source_identity'][key] == identity[key], key
    # Consume the independent standalone PC release assertions, including actual
    # installed/native role surfaces, rollback and preserved user/Todo projects.
    consumer = release['live_consumer']
    path = Path(consumer['path']).resolve(strict=True)
    assert sha(path) == consumer['sha256'], 'Changed standalone live release validator'
    spec = importlib.util.spec_from_file_location('as1_standalone_live_consumer', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.PROOF = live_path
    observed = module.live_release.__wrapped__()
    module.test_installed_and_live_standalone_pair_and_exact_role_surfaces(observed)
    module.test_actual_rollback_preserves_launcher_forward_jobs_and_native_authority(observed)
    module.test_executed_pce2_adoption_preserves_source_evidence_unrelated_work_and_nf1a(observed)
    return {'status': 'passed', 'candidate_root': str(candidate), 'cases': ['PIN-01', 'PIN-02']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT)
    parser.add_argument('--bind-evidence', action='store_true')
    parser.add_argument('--skills-qualification', type=Path)
    parser.add_argument('--skills-real-proof', type=Path)
    parser.add_argument('--live-release', type=Path)
    args = parser.parse_args()
    release = json.loads(args.manifest.read_text())
    if args.bind_evidence:
        for name, path in [('skills_qualification', args.skills_qualification), ('skills_real_proof', args.skills_real_proof), ('live_release', args.live_release)]:
            if path is None:
                parser.error(f'--bind-evidence requires --{name.replace("_", "-")}')
            path = path.resolve(strict=True)
            release['evidence'][name] = {'path': str(path), 'sha256': sha(path)}
        validate_release(release, require_passed=False)
        release['status'] = 'passed'
        args.manifest.write_text(json.dumps(release, indent=2, sort_keys=True) + '\n')
    print(json.dumps(validate_release(release), sort_keys=True))


if __name__ == '__main__':
    main()
