"""Complete skill-final grammar and bounded, unaccepted validation feedback."""
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
from test_sk_as1_observer_entry import skill_request, skill_final


def prepare(root):
    entry, resource = root / 'SKILL.md', root / 'native.md'
    entry.write_text('Read native.md as the native prerequisite.\n')
    resource.write_text('native selected fact\n')
    return entry, resource


def retained_entry(runner, entry, root):
    return runner.run(['cat', str(entry)], cwd=str(root)) | {'public_tool_call': cat(entry, root)}


def feedback(turn):
    values = [json.loads(message['content']).get('retained_observation', {})
              for message in turn['messages'] if message['role'] == 'user']
    return [value for value in values if value.get('reason') == 'skill_final_validation_failed'][-1]


def test_skill_final_example_is_complete_and_investigate_example_stays_mode_specific(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    skill_backend = Backend([cat(entry, root)])
    worker(skill_backend).run(skill_request(root, max_steps=1))
    instruction = skill_backend.turns[0]['messages'][0]['content']
    grammar = json.JSONDecoder().raw_decode(instruction.split('Final JSON: ', 1)[1])[0]
    assert set(grammar) == {'answer', 'findings', 'unresolved_questions', 'skill_selection'}
    selection = grammar['skill_selection']
    assert set(selection) == {'format', 'selections', 'synthesis', 'unresolved'}
    assert selection['format'] == 'pc-skill-selection/1'
    assert selection['selections'][0]['skill'] == 'tiny'
    assert set(selection['selections'][0]) == {'skill', 'resource', 'content_sha256', 'line_start', 'line_end', 'reason'}
    assert 'never invent a hash or select an unread or truncated resource' in instruction
    assert 'Indexes are advisory' in instruction
    ordinary = Backend([final()])
    worker(ordinary).run(request())
    ordinary_grammar = json.JSONDecoder().raw_decode(ordinary.turns[0]['messages'][0]['content'].split('Final JSON: ', 1)[1])[0]
    assert 'skill_selection' not in ordinary_grammar


def test_missing_selection_final_is_unaccepted_feedback_then_model_corrects(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    malformed = final() | {'answer': 'unaccepted proposal answer'}
    def correct(turn):
        rejection = feedback(turn)
        assert rejection['status'] == 'denied' and rejection['accepted'] is False
        assert rejection['validation_error'] == 'invalid_skill_selection'
        assert rejection['validation_data'] == {'proposed_final': malformed, 'is_source_evidence': False}
        assert 'public_tool_call' not in rejection and 'source_reads' not in rejection
        assert 'skill_selection format/selections/synthesis/unresolved' in rejection['corrective_action']
        assert len(calls_and_results(turn)) == 2  # No fabricated assistant tool call for rejected final.
        return skill_final(root) | {'answer': 'corrected native selection'}
    backend = Backend([cat(entry, root), cat(resource, root), malformed, correct])
    result = worker(backend).run(skill_request(root))
    assert result['status'] == 'completed' and result['answer'] == 'corrected native selection'
    assert result['findings'] == []
    rejection = result['observations'][2]
    assert rejection['accepted'] is False and rejection['validation_data']['proposed_final'] == malformed
    assert any(checkpoint[-1].get('accepted') is False for checkpoint in checkpoints)
    assert len(backend.turns) == 4


def test_unread_selection_feedback_does_not_auto_read_then_model_reads_missing_resource(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    retained = retained_entry(runner, entry, root)
    proposed = skill_final(root)
    def read_missing(turn):
        assert feedback(turn)['validation_error'] == 'skill_selected_resource_not_read_agentically'
        assert len(packets) == 2 and not any(packet.get('source_reads', [{}])[0].get('path') == str(resource) for packet in packets)
        return cat(resource, root)
    backend = Backend([proposed, read_missing, proposed])
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root, observations=[retained]))
    assert result['status'] == 'completed' and dispatched.call_count == 2
    assert result['observations'][1]['accepted'] is False
    assert result['observations'][2]['public_tool_call'] == cat(resource, root)


def test_q10_sized_guide_truncation_feedback_then_full_read_retains_exact_proof(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    # Exact observed Q10 dimensions, not copied content or inference proof.
    resource.write_text(('x' * 34 + '\n') * 455 + 'y' * 216 + '\n')
    assert len(resource.read_bytes()) == 16142 and len(resource.read_text().splitlines()) == 456
    selected = skill_final(root)
    selected['skill_selection']['selections'][0]['line_end'] = 456
    full = cat(resource, root)
    full['arguments']['max_output_bytes'] = 20000
    def correct_read(turn):
        assert feedback(turn)['validation_error'] == 'skill_selected_resource_not_read_agentically'
        assert 'sufficient max_output_bytes' in feedback(turn)['corrective_action']
        assert calls_and_results(turn)[1][1]['truncated'] is True
        assert 'source_reads' not in calls_and_results(turn)[1][1]
        return full
    def correct_final(turn):
        full_packet = calls_and_results(turn)[-1][1]
        assert full_packet['stdout'] == resource.read_text() and full_packet['truncated'] is False
        proof = full_packet['source_reads'][0]
        assert proof['content_sha256'] == hashlib.sha256(resource.read_bytes()).hexdigest()
        assert proof['line_count'] == 456
        return selected
    backend = Backend([cat(entry, root), cat(resource, root), selected, correct_read, correct_final])
    result = worker(backend).run(skill_request(root))
    assert result['status'] == 'completed' and len(backend.turns) == 5
    observed = [observation for observation in result['observations'] if observation.get('public_tool_call') == full][0]
    assert observed['stdout'] == resource.read_text() and observed['source_reads']
    assert 16384 < len(json.dumps(observed).encode()) <= 32768
    assert all(len(json.dumps(turn, ensure_ascii=False).encode()) <= 60000 for turn in backend.turns)
    assert any(checkpoint[-1].get('source_reads', [{}])[0].get('path') == str(resource) for checkpoint in checkpoints)


def test_repeated_missing_selection_finals_use_six_steps_then_terminal_partial(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    retained = retained_entry(runner, entry, root)
    malformed = final()
    backend = Backend([malformed] * 6)
    with patch.object(runner, 'run', wraps=runner.run) as dispatched:
        result = worker(backend).run(skill_request(root, observations=[retained]))
    assert not dispatched.called and len(backend.turns) == len(checkpoints) == 6
    assert result['status'] == 'partial' and result['reason'] == 'step_budget_exhausted'
    assert 'skill_selection' not in result and 'answer' not in result and result['findings'] == []
    assert all(observation['accepted'] is False and observation['validation_error'] == 'invalid_skill_selection'
        and 'public_tool_call' not in observation and not observation.get('source_reads')
        for observation in result['observations'][1:])


@pytest.mark.parametrize('supersede', ['before_feedback', 'during_packet_commit'])
def test_invalid_final_feedback_cannot_checkpoint_after_supersession(fixture, supersede):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    retained = retained_entry(runner, entry, root)
    generation = [1]
    backend = Backend([final()])
    if supersede == 'before_feedback':
        backend.hook = lambda: generation.__setitem__(0, 2)
    else:
        original_packetize = runner.packetize
        def superseding_packetize(payload):
            identity = original_packetize(payload)
            generation[0] = 2
            return identity
        runner.packetize = superseding_packetize
    result = worker(backend, fence=lambda job, attempt: generation[0] == attempt).run(skill_request(root, observations=[retained]))
    assert result['status'] == 'stale_attempt' and not checkpoints
    assert len(packets) == (2 if supersede == 'during_packet_commit' else 1)


def test_multiple_json_finals_are_repaired_whole_without_salvaging_prefix(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    retained = retained_entry(runner, entry, root)
    extra_data = json.dumps(final()) + '\n' + json.dumps(final())
    resource_call = cat(resource, root)
    backend = Backend([extra_data, resource_call, skill_final(root)])
    result = worker(backend).run(skill_request(root, observations=[retained], max_steps=3))
    assert result['status'] == 'completed'
    assert len(backend.turns) == 3 and len(packets) == 3
    assert result['observations'][0] == retained
    assert result['observations'][1]['public_tool_call'] == resource_call
    first_feedback = [json.loads(m['content']) for m in backend.turns[1]['messages'] if m['role'] == 'user']
    assert any(item.get('protocol_error') == 'invalid_json_object' for item in first_feedback)


def test_rejected_final_packet_cannot_support_finding_even_after_resume(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    retained = retained_entry(runner, entry, root)
    invented = final() | {'findings': [{'text': 'invented unsupported fact', 'evidence_packets': ['never-observed']}]}
    first = worker(Backend([invented])).run(skill_request(root, observations=[retained], max_steps=1))
    rejection = first['observations'][-1]
    assert rejection['validation_data']['is_source_evidence'] is False
    wrong_citation = skill_final(root, 'SKILL.md')
    wrong_citation['findings'] = [{'text': 'invented unsupported fact', 'evidence_packets': [rejection['packet_id']]}]
    correct = skill_final(root, 'SKILL.md')
    correct['findings'] = [{'text': 'The installed entry directs a native.md read.', 'evidence_packets': [retained['packet_id']]}]
    def accepted_evidence_only(turn):
        assert feedback(turn)['validation_error'] == 'finding_requires_observed_packet'
        assert feedback(turn)['accepted'] is False
        return correct
    result = worker(Backend([wrong_citation, accepted_evidence_only])).run(skill_request(root,
        attempt=2, observations=copy.deepcopy(first['observations'])))
    assert result['status'] == 'completed' and result['findings'] == correct['findings']
    assert result['findings'] != wrong_citation['findings']
    assert result['observations'][-2]['validation_data']['proposed_final'] == wrong_citation


def test_entry_denial_packet_cannot_support_source_finding_after_resume(fixture):
    from test_sk_as1_observer_entry import listing
    root, runner, packets, checkpoints, worker = fixture
    entry, resource = prepare(root)
    denied = worker(Backend([listing(root), final()])).run(skill_request(root, max_steps=2))['observations'][0]
    assert denied['accepted'] is False and denied['dispatched'] is False
    observed = retained_entry(runner, entry, root)
    invented = skill_final(root, 'SKILL.md')
    invented['findings'] = [{'text': 'invented source fact', 'evidence_packets': [denied['packet_id']]}]
    correct = skill_final(root, 'SKILL.md')
    result = worker(Backend([invented, correct])).run(skill_request(root, attempt=2, observations=[denied, observed]))
    assert result['status'] == 'completed' and result['findings'] == []
    rejection = [o for o in result['observations'] if o.get('reason') == 'skill_final_validation_failed'][0]
    assert rejection['validation_error'] == 'finding_requires_observed_packet'
    assert rejection['accepted'] is False


def test_failed_command_packet_remains_factual_failure_evidence(fixture):
    root, runner, packets, checkpoints, worker = fixture
    missing = root / 'missing.txt'
    def failure_fact(turn):
        packet = calls_and_results(turn)[0][1]
        assert packet['status'] == 'failed'
        return final() | {'findings': [{'text': 'The requested file could not be read.',
            'evidence_packets': [packet['packet_id']]}], 'unresolved_questions': ['Requested source remains unavailable.']}
    result = worker(Backend([cat(missing, root), failure_fact])).run(request())
    assert result['status'] == 'partial' and result['answer'] == 'fixture answer'
    assert result['findings'][0]['evidence_packets'] == [result['observations'][0]['packet_id']]
