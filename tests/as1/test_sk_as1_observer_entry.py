"""Pre-dispatch skill-entry feedback using actual port and real Bubblewrap."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sk_as1_observer_progress import Backend, final, fixture, request
from test_sk_as1_observer_conversation import calls_and_results, cat


def skill_request(root, **extra):
    return request(mode='skill', skill={'name': 'tiny', 'root': str(root)}, **extra)


def skill_final(root, resource='native.md'):
    path = root / resource
    return final() | {'skill_selection': {'format': 'pc-skill-selection/1', 'synthesis': 'native selection',
        'selections': [{'skill': 'tiny', 'resource': resource, 'reason': 'native prerequisite',
            'content_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'line_start': 1, 'line_end': 1}]}}


def listing(root):
    return {'tool': 'command', 'arguments': {'argv': ['find', str(root), '-maxdepth', '2'], 'cwd': str(root)}}


def test_first_find_is_denied_before_dispatch_then_native_entry_resource_final_succeeds(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = root / 'SKILL.md', root / 'native.md'
    entry.write_text('Read native.md as the installed native prerequisite.\n')
    resource.write_text('native selected fact\n')
    wrong_call = listing(root)
    def choose_entry(turn):
        proposed, denial = calls_and_results(turn)[0]
        assert proposed == wrong_call
        assert denial['status'] == 'denied' and denial['reason'] == 'skill_entry_required'
        assert denial['dispatched'] is False and denial['required_skill_entry'] == str(entry)
        assert 'source_reads' not in denial and 'stdout' not in denial
        assert 'successfully with direct cat' in denial['corrective_action']
        return cat(entry, root)
    def follow_native_map(turn):
        assert calls_and_results(turn)[-1][1]['stdout'] == entry.read_text()
        return cat(resource, root)
    backend = Backend([wrong_call, choose_entry, follow_native_map, skill_final(root)])
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root))
    assert result['status'] == 'completed' and result['authoritative'] is False
    assert [call.kwargs['argv'] if 'argv' in call.kwargs else call.args[0]
            for call in dispatched.call_args_list] == [['cat', str(entry)], ['cat', str(resource)], ['cat', str(resource)]]
    assert result['observations'][0]['public_tool_call'] == wrong_call
    assert packets[0]['dispatched'] is False and 'public_tool_call' not in packets[0]
    assert all(not observation.get('source_reads') for observation in result['observations'][:1])
    assert checkpoints[-1] == result['observations']
    assert result['observations'][1]['source_reads'][0]['path'] == str(entry)


def test_repeated_entry_refusal_uses_original_six_steps_and_terminates(fixture):
    root, runner, packets, checkpoints, worker = fixture
    (root / 'SKILL.md').write_text('installed entry\n')
    backend = Backend([listing(root)] * 6)
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root))
    assert not dispatched.called
    assert result['status'] == 'partial' and result['reason'] == 'step_budget_exhausted'
    assert result['unresolved_questions'] and 'skill_selection' not in result
    assert len(backend.turns) == len(packets) == len(checkpoints) == len(result['observations']) == 6
    assert all(observation['status'] == 'denied' and observation['dispatched'] is False
               and 'source_reads' not in observation for observation in result['observations'])


def test_semantic_call_and_downstream_cat_cannot_run_before_entry(fixture):
    root, runner, packets, checkpoints, worker = fixture
    (root / 'SKILL.md').write_text('Read native.md\n')
    resource = root / 'native.md'
    resource.write_text('do not read before entry\n')
    proposals = [{'tool': 'search', 'arguments': {'query': 'native prerequisite'}}, cat(resource, root)]
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(Backend(proposals)).run(skill_request(root, max_steps=2))
    assert not dispatched.called
    assert result['reason'] == 'step_budget_exhausted'
    assert [observation['public_tool_call'] for observation in result['observations']] == proposals
    assert all(observation['reason'] == 'skill_entry_required' for observation in result['observations'])


def test_resumed_successful_entry_proof_authorizes_native_reference_without_reread(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = root / 'SKILL.md', root / 'native.md'
    entry.write_text('Read native.md\n')
    resource.write_text('native selected fact\n')
    retained = runner.run(['cat', str(entry)], cwd=str(root)) | {'public_tool_call': cat(entry, root)}
    backend = Backend([cat(resource, root), skill_final(root)])
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root, observations=[copy.deepcopy(retained)]))
    assert result['status'] == 'completed'
    assert len(dispatched.call_args_list) == 2
    assert all((call.kwargs.get('argv') or call.args[0]) == ['cat', str(resource)] for call in dispatched.call_args_list)
    assert result['observations'][0] == retained
    assert calls_and_results(backend.turns[0])[0][0] == cat(entry, root)


@pytest.mark.parametrize('failure', ['truncated', 'missing'])
def test_failed_or_truncated_entry_cannot_route_or_finalize_and_is_retained(fixture, failure):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = root / 'SKILL.md', root / 'native.md'
    resource.write_text('native fact\n')
    proposed = cat(entry, root)
    if failure == 'truncated':
        entry.write_text('entry longer than selected byte limit\n')
        proposed['arguments']['max_output_bytes'] = 5
    def blocked_route(turn):
        previous = calls_and_results(turn)[0][1]
        assert 'source_reads' not in previous
        assert previous['truncated'] if failure == 'truncated' else previous['status'] == 'failed'
        assert 'Failed or truncated entry observations do not satisfy' in turn['messages'][-1]['content']
        return cat(resource, root)
    backend = Backend([proposed, blocked_route, skill_final(root)])
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root))
    assert dispatched.call_count == 1
    assert result['status'] == 'partial' and result['reason'] == 'skill_installed_entry_not_read_agentically'
    assert 'skill_selection' not in result and 'answer' not in result
    assert len(result['observations']) == len(checkpoints) == 2
    assert result['observations'][0]['public_tool_call'] == proposed
    assert result['observations'][1]['status'] == 'denied'
    assert not any(observation.get('source_reads') for observation in result['observations'])


def test_truncated_entry_feedback_allows_model_to_choose_complete_read(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = root / 'SKILL.md', root / 'native.md'
    entry.write_text('Read native.md after full installed entry.\n')
    resource.write_text('native fact\n')
    truncated = cat(entry, root)
    truncated['arguments']['max_output_bytes'] = 5
    backend = Backend([truncated, cat(entry, root), cat(resource, root), skill_final(root)])
    result = worker(backend).run(skill_request(root))
    assert result['status'] == 'completed' and len(backend.turns) == 4
    assert result['observations'][0]['truncated'] is True
    assert 'source_reads' not in result['observations'][0]
    assert result['observations'][1]['source_reads'][0]['path'] == str(entry)


@pytest.mark.parametrize('supersede', ['before_denial', 'during_packet_commit'])
def test_policy_denial_is_fenced_and_never_checkpoints_after_supersession(fixture, supersede):
    root, runner, packets, checkpoints, worker = fixture
    (root / 'SKILL.md').write_text('installed entry\n')
    generation = [1]
    backend = Backend([listing(root)])
    if supersede == 'before_denial':
        backend.hook = lambda: generation.__setitem__(0, 2)
    else:
        original_packetize = runner.packetize
        def superseding_packetize(payload):
            identity = original_packetize(payload)
            generation[0] = 2
            return identity
        runner.packetize = superseding_packetize
    result = worker(backend, fence=lambda job, attempt: generation[0] == attempt).run(skill_request(root))
    assert result['status'] == 'stale_attempt' and not checkpoints
    assert len(packets) == (1 if supersede == 'during_packet_commit' else 0)
    if packets:
        assert packets[0]['status'] == 'denied' and packets[0]['dispatched'] is False


def test_relative_direct_cat_identifies_the_same_canonical_entry(fixture):
    root, runner, packets, checkpoints, worker = fixture
    (root / 'SKILL.md').write_text('canonical installed entry\n')
    (root / 'native.md').write_text('native selected fact\n')
    relative = {'tool': 'command', 'arguments': {'argv': ['/usr/bin/cat', './SKILL.md'], 'cwd': str(root)}}
    result = worker(Backend([relative, cat(root / 'native.md', root), skill_final(root)])).run(skill_request(root))
    assert result['status'] == 'completed'
    assert result['observations'][0]['public_tool_call'] == relative
    assert result['observations'][0]['source_reads'][0]['path'] == str(root / 'SKILL.md')
