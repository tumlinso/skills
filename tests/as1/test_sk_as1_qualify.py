"""Paired qualification: installed runtime effects and source-bound real proof.

Only the subprocess fixture mutates Todo, exclusively below pytest's tmp_path.
Live inference is executed by the separately authorized GPU qualification worker.
Missing hardware proof is a failure, never a skip or scripted substitute.
"""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

SKILLS = Path(__file__).resolve().parents[2]
PC_COMMIT = os.environ.get('AS1_SQA_PC_COMMIT', '3905649ff9b03e3acec4211553a52cf2389489e9')
SK_COMMIT = os.environ.get('AS1_SQA_SK_COMMIT', '269646d2da7452adfb5750bfe9b7a3068f7ee828')
CANDIDATE = Path(os.environ.get('AS1_SQA_CANDIDATE', '/home/tumlinson/.local/share/project-control/candidates/as1-paired-3905649-269646d-20261005'))
PROOF = Path(os.environ.get('AS1_SQA_PROOF', str(SKILLS / 'planning/adaptive-surface-v1/validation/sqa-real' / (CANDIDATE.name + '-q14') / 'receipt.json')))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def candidate_environment(tmp_path):
    manifest = CANDIDATE / 'release-manifest.json'
    assert manifest.is_file(), 'Exact paired candidate must be built before qualification'
    release = json.loads(manifest.read_text())
    assert release['project_control_commit'] == PC_COMMIT
    assert release['todo_commit'] == SK_COMMIT
    assert Path(release['skills_root']) == CANDIDATE / 'runtime-skills'
    env = {k: v for k, v in os.environ.items() if not k.startswith(('PROJECT_CONTROL_', 'CODING_WORKFLOW_', 'TODO_ORCHESTRATOR_')) and k != 'PYTHONPATH'}
    env.update(AS1_SQA_CANDIDATE=str(CANDIDATE), AS1_SQA_SK_COMMIT=SK_COMMIT, PROJECT_CONTROL_SKILLS_ROOT=release['skills_root'],
               PROJECT_CONTROL_RELEASE_MANIFEST=str(manifest),
               PROJECT_CONTROL_RELEASE_DIGEST=sha(manifest),
               XDG_STATE_HOME=str(tmp_path / 'state'), PYTHONDONTWRITEBYTECODE='1')
    return env


def run_candidate(journey, tmp_path):
    env = candidate_environment(tmp_path)
    result = subprocess.run([str(CANDIDATE / 'bin/python'), str(Path(__file__).with_name('sqa_candidate_journeys.py')),
                             '--journey', journey, str(tmp_path)],
                            env=env, text=True, capture_output=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.splitlines()[-1])


@pytest.mark.as1_case('SQA-01')
def test_installed_identity_profiles_canonical_reads_and_native_workflow(tmp_path):
    result = run_candidate('workflow', tmp_path)
    assert result['status'] == 'passed'
    assert result['canonical_reads'] == ['status', 'ready', 'semantic.state', 'semantic.workflow']
    assert result['fixture_completion'] == 'done'
    assert result['roles'] == ['observer', 'investigator', 'skill_assembler', 'coder', 'codex', 'mutator']


@pytest.mark.as1_case('SQA-02')
def test_installed_dormant_delegation_is_preserved_but_dispatch_inactive(tmp_path):
    assert run_candidate('delegation', tmp_path)['status'] == 'passed'


@pytest.mark.as1_case('SQA-02')
def test_real_scout_skill_eviction_proof_is_bound_to_exact_candidate(tmp_path):
    candidate_environment(tmp_path)
    assert PROOF.is_file(), 'Required actual inference proof has not been executed'
    proof = json.loads(PROOF.read_text())
    assert proof['format'] == 'as1-paired-realproof/1'
    identity = proof['source_identity']
    assert identity['candidate_root'] == str(CANDIDATE)
    assert identity['pc_commit'] == PC_COMMIT
    assert identity['skills_commit'] == SK_COMMIT
    assert identity['release_sha256'] == sha(CANDIDATE / 'release-manifest.json')
    for key, relative in (('observer_runtime_sha256', 'local-coding-worker/local_worker/observer_runtime.py'),
                          ('native_catalog_sha256', 'integrations/native-skill-catalog.json'),
                          ('native_routing_sha256', 'integrations/native-skill-routing.md')):
        assert identity[key] == sha(CANDIDATE / 'runtime-skills' / relative), key
    assert proof['status'] == 'passed'
    assert proof['artifacts']
    for relative, expected in proof['artifacts'].items():
        path = (PROOF.parent / relative).resolve()
        assert path.is_relative_to(PROOF.parent.resolve()), 'Proof artifact escapes evidence directory'
        assert sha(path) == expected
    for name in ('scout', 'skill', 'eviction', 'restart', 'checkpoint', 'poll'):
        assert proof['journeys'][name]['status'] == 'passed', name
        assert proof['journeys'][name]['artifact'] in proof['artifacts'], name
    def artifact(name):
        relative = proof['journeys'][name]['artifact'] if name in proof['journeys'] else name + '.json'
        assert relative in proof['artifacts'], relative
        return json.loads((PROOF.parent / relative).read_text())
    scout = artifact('scout')
    assert scout['job']['mode'] == 'investigate'
    assert scout['job']['status'] == 'completed' and scout['job']['result_packet']
    assert scout['observations'] and scout['job']['hints']
    skill = artifact('skill')
    assert skill['status'] in ('completed', 'partial') and skill['excerpts']
    for excerpt in skill['excerpts']:
        resource = (CANDIDATE / 'runtime-skills' / excerpt['skill'] / excerpt['resource']).resolve()
        assert resource.is_relative_to(CANDIDATE / 'runtime-skills')
        assert sha(resource) == excerpt['content_sha256']
        assert excerpt['verbatim'] is True and excerpt['authority'] == 'direct original text'
        exact = ''.join(resource.read_text().splitlines(keepends=True)[excerpt['line_start'] - 1:excerpt['line_end']])
        assert exact and exact == excerpt['content']
    # Q11's actual agent-owned routing and source selections are reused with
    # explicit provenance. Its incorrect narrative never becomes verified truth.
    reuse = artifact('reused_skill_proof')
    assert reuse['format'] == 'as1-reused-native-skill-proof/1'
    assert reuse['semantic_finding_verified'] is False and reuse['new_skill_model_calls'] == 0
    assert reuse['limitations'] and reuse['actual_prior_model_turns'] > 0
    original_path = Path(reuse['source_receipt'])
    assert sha(original_path) == reuse['source_receipt_sha256']
    original = json.loads(original_path.read_text())
    assert original['status'] == reuse['original_helper_receipt_status'] == 'failed'
    equivalence = artifact('skill_source_equivalence')
    assert equivalence['format'] == 'as1-skill-source-equivalence/1'
    assert equivalence['historical_phase_identity'] == original['source_identity']
    assert equivalence['current_phase_identity'] == identity
    assert equivalence['semantic_finding_verified'] is False
    for key in ('skills_commit', 'observer_runtime_sha256', 'native_catalog_sha256', 'native_routing_sha256'):
        assert original['source_identity'][key] == identity[key]
    historical_candidate = Path(original['source_identity']['candidate_root'])
    assert sha(historical_candidate / 'release-manifest.json') == original['source_identity']['release_sha256']
    historical_skills = historical_candidate / 'runtime-skills'
    historical_pc = next((historical_candidate / 'lib').glob('python*/site-packages/project_control'))
    current_pc = next((CANDIDATE / 'lib').glob('python*/site-packages/project_control'))
    assert set(equivalence['unchanged_pc_modules_sha256']) == {'as1_skill.py', 'profiles.py', 'as1_surface.py'}
    for relative, expected in equivalence['unchanged_pc_modules_sha256'].items():
        assert sha(historical_pc / relative) == sha(current_pc / relative) == expected
    factory_binding = equivalence['qualified_factory_callback_equivalence']
    assert sha(current_pc / 'as1_jobs.py') == factory_binding['qualified_as1_jobs_sha256'] == '592ae8e5576eb94dc5a2d64c5c35ad358a8bbb552bc8c6a57eebc299c69201ad'
    def factory_ast(path, protective_adapter):
        text = path.read_text(); tree = ast.parse(text)
        node = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'TrustedObserverFactory')
        original = ast.dump(node, include_attributes=False)
        method = next(item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == '__call__')
        block = []
        if protective_adapter:
            assert isinstance(method.body[-1], ast.Return)
            block = method.body[-4:-1]
            assert len(block) == 3 and isinstance(block[0], ast.Assign)
            assert [target.id for target in block[0].targets] == ['scope']
            assert isinstance(block[1], ast.FunctionDef) and block[1].name == 'fence'
            assert isinstance(block[2], ast.FunctionDef) and block[2].name == 'checkpoint'
            del method.body[-4:-1]
        block_ast = ast.dump(ast.Module(body=block, type_ignores=[]), include_attributes=False)
        constructors = [item for item in ast.walk(node) if isinstance(item, ast.Call)
                        and isinstance(item.func, ast.Attribute) and item.func.attr == 'ObserverWorkerPort']
        assert len(constructors) == 1
        callbacks = {}
        for keyword in constructors[0].keywords:
            if keyword.arg in ('fence', 'checkpoint'):
                callbacks[keyword.arg] = {'source': ast.unparse(keyword.value),
                                         'ast_sha256': hashlib.sha256(ast.dump(keyword.value, include_attributes=False).encode()).hexdigest()}
                keyword.value = ast.Name(id='QUALIFIED_' + keyword.arg.upper() + '_CALLBACK', ctx=ast.Load())
        assert set(callbacks) == {'fence', 'checkpoint'}
        return {'full_factory_ast_sha256': hashlib.sha256(original.encode()).hexdigest(),
                'normalized_factory_ast_sha256': hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest(),
                'adapter_source': [ast.get_source_segment(text, item) for item in block],
                'adapter_ast_sha256': hashlib.sha256(block_ast.encode()).hexdigest(), 'callbacks': callbacks}
    historical_factory = factory_ast(historical_pc / 'as1_jobs.py', False)
    current_factory = factory_ast(current_pc / 'as1_jobs.py', True)
    assert historical_factory == factory_binding['historical']
    assert current_factory == factory_binding['current']
    assert historical_factory['normalized_factory_ast_sha256'] == current_factory['normalized_factory_ast_sha256']
    evidence = factory_binding['qualified_evidence']
    assert set(evidence) == {'native_checkpoint_regressions', 'affected_surface_regressions', 'independent_static_review'}
    for label, item in evidence.items():
        assert sha(Path(item['path'])) == item['sha256']
        assert json.loads(Path(item['path']).read_text()) == item['data']
        if label.endswith('regressions'):
            report = item['data']
            assert report['pytest_exitstatus'] == 0
            assert all(row['outcome'] == 'passed' for rows in report['cases'].values() for row in rows)
            assert len({row['test'] for rows in report['cases'].values() for row in rows}) == (24 if label == 'native_checkpoint_regressions' else 2)
        else:
            assert item['data']['status'] == 'clean' and not item['data']['blocking_findings']
            assert item['data']['source_sha256'] == factory_binding['qualified_as1_jobs_sha256']
    for relative, expected in equivalence['unchanged_skill_inputs_sha256'].items():
        assert sha(historical_skills / relative) == sha(CANDIDATE / 'runtime-skills' / relative) == expected
    assert original['artifacts'] == reuse['source_artifacts_sha256']
    for relative, expected in original['artifacts'].items():
        path = (original_path.parent / relative).resolve()
        assert path.is_relative_to(original_path.parent.resolve())
        assert sha(path) == expected
    original_skill = json.loads((original_path.parent / 'skill.json').read_text())
    assert skill == original_skill
    skill_job = artifact('skill_job')
    assert skill_job == json.loads((original_path.parent / 'skill_job.json').read_text())
    assert skill_job['job']['mode'] == 'skill' and skill_job['job']['status'] == 'completed'
    reads = {}
    for index, observation in enumerate(skill_job['observations']):
        for read in observation.get('source_reads', []):
            historical_path = Path(read['path']).resolve()
            assert historical_path.is_relative_to(historical_skills.resolve())
            relative = historical_path.relative_to(historical_skills.resolve())
            current_path = CANDIDATE / 'runtime-skills' / relative
            assert read['content_sha256'] == sha(historical_path) == sha(current_path)
            reads[str(current_path)] = {**read, 'index': index}
    order = []
    for relative in ('SKILL.md', 'references/legacy-skill-router.md', 'references/architectures/volta/router.md'):
        path = CANDIDATE / 'runtime-skills/cuda' / relative
        proof_read = reads[str(path)]
        assert proof_read['method'] == 'direct_cat' and proof_read['content_sha256'] == sha(path)
        order.append(proof_read['index'])
    assert order[0] < order[1] < order[2] and order == reuse['required_read_order']
    for excerpt in skill['excerpts']:
        resource = CANDIDATE / 'runtime-skills' / excerpt['skill'] / excerpt['resource']
        assert reads[str(resource)]['method'] == 'direct_cat'
        assert reads[str(resource)]['content_sha256'] == sha(resource)
        assert order[0] <= reads[str(resource)]['index']
    assert skill['synthesis']['label'] == 'local-agent synthesis; not authoritative source text'
    assert skill['synthesis']['entailment_verified'] is False
    original_turns = json.loads((original_path.parent / 'turns.json').read_text())
    assert len(original_turns) == reuse['actual_prior_model_turns']
    assert json.loads(original_turns[-1]['response']['text'])['skill_selection']
    for turn in original_turns:
        assert turn['model_id'] and turn['model_pid'] > 0
        assert turn['request']['messages'] and turn['response']['text']
        assert turn['response']['status'] == 'available'
        assert turn['response']['usage']['completion_tokens'] > 0
    eviction = artifact('eviction')
    before_pid = eviction['initial_session']['server_pid']
    after_pid = eviction['reloaded_session']['server_pid']
    assert before_pid > 0 and after_pid > 0 and before_pid != after_pid
    assert any(row['owned_pid'] == before_pid and row['released'] is True
               for row in eviction['cleanup_receipts'])
    restart = artifact('restart')
    assert restart['dispatcher_before'] == 'stopped'
    assert restart['dispatcher_after']['dispatcher'] == 'running'
    assert restart['model_reloaded_independently'] is True
    assert restart['model_before_pid'] == before_pid and restart['model_after_pid'] == after_pid
    assert restart['after_attempt'] > restart['before_attempt']
    checkpoint = artifact('checkpoint')
    retained = checkpoint['retained_packet_ids']
    assert retained and checkpoint['no_repeated_source_read'] and checkpoint['preserved_observations']
    assert checkpoint['after_attempt'] > checkpoint['before_attempt']
    assert set(retained) <= {row['packet_id'] for row in scout['observations']}
    initial = artifact('checkpoint_before')
    initial_reads = [r['path'] for row in initial['observations'] for r in row.get('source_reads', [])]
    resumed_reads = [r['path'] for row in scout['observations'] for r in row.get('source_reads', [])]
    assert initial_reads
    assert all(resumed_reads.count(path) == initial_reads.count(path) for path in initial_reads)
    poll = artifact('poll')
    assert poll['starts_no_model'] is True
    assert poll['poll']['job']['job_id'] == scout['job']['job_id']
    assert poll['poll']['job']['status'] == 'yielding'
    busy = artifact('busy_admissions')
    assert len(busy) >= 2 and all(row['accepted'] for row in busy)
    assert 'busy' in json.dumps(busy).lower()
    queued = artifact('queued_results')
    assert {row['job']['job_id'] for row in queued} == {row['job_id'] for row in busy}
    outcomes = artifact('queued_outcomes')
    expected_counts = {status: sum(row['job']['status'] == status for row in queued)
                       for status in ('completed', 'partial')}
    assert outcomes['status_counts'] == expected_counts and sum(expected_counts.values()) == len(queued)
    assert {row['job_id'] for row in outcomes['outcomes']} == {row['job']['job_id'] for row in queued}
    for row in queued:
        job = row['job']
        assert job['status'] in ('completed', 'partial') and job['result_packet']
        assert job['scope'] == scout['job']['scope']
        observed_ids = {observation['packet_id'] for observation in row['observations']}
        assert all(set(finding['evidence_packets']) <= observed_ids for finding in job['findings'])
        outcome = next(item for item in outcomes['outcomes'] if item['job_id'] == job['job_id'])
        assert outcome['status'] == job['status'] and outcome['result_packet'] == job['result_packet']
        assert outcome['accepted_findings'] == job['findings']
        if job['status'] == 'partial':
            assert outcome['reason'] and job['unresolved_questions']
            assert outcome['unresolved_questions'] == job['unresolved_questions']

    foreground = artifact('foreground')
    assert foreground['result']['ok'] is True and foreground['cleanup_receipts']
    cleanup = artifact('cleanup')
    assert not cleanup['remaining_slots'] and not cleanup['remaining_owned_leases']
    assert cleanup['unrelated_before'] == cleanup['unrelated_after']
    assert cleanup['protected_identity_before'] == cleanup['protected_identity_after']
    assert cleanup['observation']['available'] is True and not cleanup['observation']['processes']
    assert all(row['memory_used_mib'] == 0 for row in cleanup['observation']['devices'])
    # The real worker owns substantive journey assertions; these mandatory raw
    # turn records exclude a typed success declaration as qualification proof.
    turns = json.loads((PROOF.parent / proof['inference_artifact']).read_text())
    assert turns and proof['inference_artifact'] in proof['artifacts']
    for turn in turns:
        assert turn['model_id'] and turn['model_pid'] > 0
        assert turn['request']['messages'] and turn['response']['text']
        assert turn['response']['status'] == 'available'
        assert turn['response']['usage']['completion_tokens'] > 0


@pytest.mark.as1_case('SQA-03')
def test_exact_skills_producer_consumption_and_native_route_provenance(tmp_path):
    assert run_candidate('provenance', tmp_path)['status'] == 'passed'
