"""Read-only standalone paired release consumer and post-proof manifest binding.

Binding writes only the explicit Skills release manifest, never runtime or Todo.
Qualification and live effects must already have been executed by their owners.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import hashlib

SKILLS = Path(__file__).resolve().parents[1]
DEFAULT = SKILLS / 'integrations/as1-paired-release.json'


class ReleaseValidationError(ValueError):
    """A paired release or its evidence does not meet the pinned contract."""


def require(condition, message):
    """Keep release gates active under optimized Python execution."""
    if not condition:
        raise ReleaseValidationError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_bound(reference):
    path = Path(reference['path']).resolve(strict=True)
    require(reference['sha256'] and sha(path) == reference['sha256'], f'Unbound or changed artifact: {path}')
    return path, json.loads(path.read_text())


def passing_cases(report, cases):
    if report.get('kind') == 'executed_product_acceptance':
        require(report.get('status') == 'passed' and report.get('pytest_returncode') == 0, 'Qualification failed')
        require(report.get('outcome') == 'SK-AS1-QUALIFY', 'Qualification outcome differs')
        require(report.get('test_file') == 'tests/as1/test_sk_as1_qualify.py', 'Qualification test source differs')
        require(not report.get('missing_or_failed_cases'), 'Qualification cases failed or missing')
        require(cases == set(report.get('required_cases', ())) == set(report.get('passed_cases', ())),
                'Qualification coverage differs')
        return
    require(report.get('pytest_exitstatus') == 0, 'Qualification failed')
    for case in cases:
        rows = report.get('cases', {}).get(case)
        require(rows and all(row.get('outcome') == 'passed' for row in rows), case)


def validate_receiver(candidate, installed, manifest):
    """Prove the candidate contains and binds the Project Control receiver."""
    binding = installed.get('local_runtime_binding')
    require(isinstance(binding, dict), 'Candidate has no Project Control local runtime binding')
    require(binding.get('path') == 'project_control/local_runtime', 'Candidate runtime path is not receiver-owned')
    manifest_sha = binding.get('manifest_sha256')
    fingerprint = binding.get('fingerprint')
    require(isinstance(manifest_sha, str) and len(manifest_sha) == 64, 'Invalid receiver manifest pin')
    require(isinstance(fingerprint, str) and len(fingerprint) == 64, 'Invalid receiver fingerprint pin')

    # Some venvs expose `lib64` as an alias of `lib`; deduplicate only by
    # canonical path and reject two genuinely distinct installed receivers.
    receiver_manifests = {
        path.resolve(strict=True)
        for path in candidate.glob('lib*/python*/site-packages/project_control/local_runtime/receiver-manifest.json')
    }
    require(len(receiver_manifests) == 1, 'Candidate must contain one installed Project Control receiver')
    receiver_manifest = next(iter(receiver_manifests))
    require(sha(receiver_manifest) == manifest_sha, 'Candidate receiver manifest differs from release pin')
    receiver_root = receiver_manifest.parent
    package = receiver_root.parent
    binding_path = package.parent / binding['path']
    require(package.name == 'project_control' and receiver_root == package / 'local_runtime',
            'Candidate receiver package layout is invalid')
    require(binding_path == receiver_root, 'Receiver binding is outside the installed package')

    interpreter = candidate / 'bin/python'
    require(interpreter.is_file(), 'Candidate interpreter is missing')
    # Ignore ambient Python paths, user site packages, .pth files, and
    # sitecustomize. Add only the package root proved to be inside this venv.
    site_packages = package.parent.resolve(strict=True)
    require(site_packages.is_relative_to(candidate.resolve()), 'Candidate package root escaped its venv')
    environment = {
        'PATH': os.defpath,
        'PROJECT_CONTROL_RELEASE_MANIFEST': str(manifest.resolve(strict=True)),
        'PROJECT_CONTROL_RELEASE_DIGEST': sha(manifest),
    }
    probe_code = '''
import json, sys, sysconfig
from pathlib import Path
site_packages = Path(sys.argv[1]).resolve(strict=True)
stdlib = Path(sysconfig.get_paths()["stdlib"]).resolve(strict=True)
stdlib_paths = []
for value in sys.path:
    if not value:
        continue
    try:
        path = Path(value).resolve()
    except OSError:
        continue
    if path == stdlib or path.is_relative_to(stdlib):
        stdlib_paths.append(str(path))
sys.path[:] = [str(site_packages), *stdlib_paths]
import project_control.runtime_binding as binding
expected_module = (site_packages / "project_control/runtime_binding.py").resolve(strict=True)
observed_module = Path(binding.__file__).resolve(strict=True)
if observed_module != expected_module:
    raise RuntimeError("candidate_runtime_binding_origin_mismatch")
identity = binding.bind_local_runtime()
print(json.dumps({"manifest_sha256": identity.manifest_sha256,
                  "fingerprint": identity.fingerprint,
                  "root": str(identity.root),
                  "binding_module": str(observed_module)}))
'''
    probe = subprocess.run(
        [str(interpreter), '-I', '-S', '-B', '-c', probe_code, str(site_packages)],
        cwd=candidate, env=environment, capture_output=True, text=True, check=True, timeout=30)
    observed = json.loads(probe.stdout.splitlines()[-1])
    require(observed.get('manifest_sha256') == manifest_sha, 'Candidate binder observed another receiver manifest')
    require(observed.get('fingerprint') == fingerprint, 'Candidate binder observed another receiver fingerprint')
    require(Path(observed['root']).resolve() == receiver_root.resolve(),
            'Candidate binder selected another runtime root')
    require(Path(observed['binding_module']).resolve() == (package / 'runtime_binding.py').resolve(),
            'Candidate binder module origin changed')
    return {'manifest_sha256': manifest_sha, 'fingerprint': fingerprint}


def _validate_identity(release):
    require(release.get('format') == 'skills-as1-paired-release/1', 'Paired release format is unsupported')
    candidate = Path(release['candidate']['path']).resolve(strict=True)
    manifest = candidate / 'release-manifest.json'
    require(sha(manifest) == release['candidate']['manifest_sha256'], 'Candidate release manifest digest differs')
    installed = json.loads(manifest.read_text())
    require(installed.get('project_control_commit') == release['pins']['project_control'],
            'Candidate Project Control source pin differs')
    require(installed.get('todo_commit') == release['pins']['skills'], 'Candidate Skills source pin differs')
    require(Path(installed['skills_root']).resolve() == candidate / 'runtime-skills',
            'Candidate Skills root escaped its release directory')
    receiver = validate_receiver(candidate, installed, manifest)
    for relative, expected in installed.get('frozen_skill_resources', {}).items():
        resource = (candidate / 'runtime-skills' / relative).resolve(strict=True)
        require(resource.is_relative_to(candidate / 'runtime-skills'), f'Frozen skill resource escaped candidate: {relative}')
        require(sha(resource) == expected, relative)
    entries = subprocess.check_output(['git', 'ls-files', '--stage', '-z'], cwd=SKILLS).decode().split('\0')
    for entry in filter(None, entries):
        metadata, name = entry.split('\t', 1)
        require(metadata.split()[0] != '160000', f'Skills must be standalone: gitlink {name}')
        path = Path(name)
        if path.suffix == '.py':
            require(not {'project-control', 'project_control'} & set(path.parts),
                    f'Project Control source copy: {name}')
    require(not (SKILLS / 'project-control').exists(),
            'Standalone Skills must not contain a second Project Control checkout')
    require(not (SKILLS / 'project_control').exists(),
            'Standalone Skills must not contain a Project Control source copy')
    instructions = release['instructions']
    path = (SKILLS / instructions['path']).resolve(strict=True)
    require(path.is_relative_to(SKILLS) and sha(path) == instructions['sha256'],
            'Paired release instructions changed or escaped Skills root')
    return candidate, receiver


def _validate_live_consumer(path, proof_path, expected_sha256):
    """Run the pinned assertion-based source consumer without inherited -O."""
    probe = '''
import hashlib, importlib.util, sys, types
from pathlib import Path
pytest_stub = types.ModuleType("pytest")
def fixture(function):
    function.__wrapped__ = function
    return function
pytest_stub.fixture = fixture
pytest_stub.mark = types.SimpleNamespace(as1_case=lambda _case: (lambda function: function))
sys.modules["pytest"] = pytest_stub
consumer_path = Path(sys.argv[1]).resolve(strict=True)
proof_path = Path(sys.argv[2]).resolve(strict=True)
source = consumer_path.read_bytes()
if hashlib.sha256(source).hexdigest() != sys.argv[3]:
    raise RuntimeError("standalone_live_consumer_changed_before_execution")
spec = importlib.util.spec_from_file_location("as1_standalone_live_consumer", consumer_path)
if spec is None or spec.loader is None:
    raise RuntimeError("standalone_live_consumer_import_failed")
module = importlib.util.module_from_spec(spec)
exec(compile(source, str(consumer_path), "exec", dont_inherit=True), module.__dict__)
module.PROOF = proof_path
observed = module.live_release.__wrapped__()
module.test_installed_and_live_standalone_pair_and_exact_role_surfaces(observed)
module.test_actual_rollback_preserves_launcher_forward_jobs_and_native_authority(observed)
module.test_executed_pce2_adoption_preserves_source_evidence_unrelated_work_and_nf1a(observed)
'''
    environment = {'PATH': os.defpath}
    result = subprocess.run(
        [sys.executable, '-I', '-S', '-B', '-c', probe, str(path), str(proof_path), expected_sha256],
        cwd=path.parent, env=environment, capture_output=True, text=True, timeout=120)
    require(result.returncode == 0,
            f'Standalone live release source validation failed: {result.stderr[-1000:]}')


def validate_identity(release):
    """Validate candidate source pins and return its path (legacy API)."""
    candidate, _ = _validate_identity(release)
    return candidate


def validate_release(release, *, require_passed=True):
    candidate, receiver = _validate_identity(release)
    if require_passed:
        require(release.get('status') == 'passed', 'Paired release pending actual qualification and live release proof')
    evidence = release['evidence']
    _, qualification = read_bound(evidence['skills_qualification'])
    passing_cases(qualification, {'SQA-01', 'SQA-02', 'SQA-03'})
    proof_path, proof = read_bound(evidence['skills_real_proof'])
    require(proof.get('format') == 'as1-paired-realproof/1' and proof.get('status') == 'passed',
            'Paired real proof is missing or failed')
    identity = proof['source_identity']
    require(Path(identity['candidate_root']).resolve() == candidate, 'Real proof identifies another candidate')
    require(identity['pc_commit'] == release['pins']['project_control'], 'Real proof Project Control pin differs')
    require(identity['skills_commit'] == release['pins']['skills'], 'Real proof Skills pin differs')
    require(identity['release_sha256'] == release['candidate']['manifest_sha256'], 'Real proof release digest differs')
    require(identity.get('receiver_manifest_sha256') == receiver['manifest_sha256'],
            'Real proof receiver manifest differs')
    require(identity.get('receiver_fingerprint') == receiver['fingerprint'], 'Real proof receiver fingerprint differs')
    require(bool(proof.get('artifacts')), 'Real proof contains no artifacts')
    for relative, expected in proof['artifacts'].items():
        path = (proof_path.parent / relative).resolve(strict=True)
        require(path.is_relative_to(proof_path.parent), f'Real proof artifact escaped its receipt: {relative}')
        require(sha(path) == expected, relative)
    for name in ('scout', 'skill', 'eviction', 'restart', 'checkpoint', 'poll'):
        journey = proof.get('journeys', {}).get(name, {})
        require(journey.get('status') == 'passed', f'Real proof journey did not pass: {name}')
        require(journey.get('artifact') in proof['artifacts'], f'Real proof journey artifact missing: {name}')
    live_path, live = read_bound(evidence['live_release'])
    require(live.get('format') == 'pc-as1-live-release/1' and live.get('status') == 'passed',
            'Live release proof is missing or failed')
    for key in ('candidate_root', 'pc_commit', 'skills_commit', 'release_sha256',
                'receiver_manifest_sha256', 'receiver_fingerprint'):
        require(live.get('source_identity', {}).get(key) == identity[key], f'Live release source identity differs: {key}')
    # Consume the independent standalone PC release assertions, including actual
    # installed/native role surfaces, rollback and preserved user/Todo projects.
    consumer = release['live_consumer']
    path = Path(consumer['path']).resolve(strict=True)
    require(sha(path) == consumer['sha256'], 'Changed standalone live release validator')
    _validate_live_consumer(path, live_path, consumer['sha256'])
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
