"""Real-port public conversation tests; no inference or hidden reasoning fixture."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sk_as1_observer_progress import Backend, example, final, fixture, request, runtime


def value(message):
    return json.loads(message['content'])


def calls_and_results(turn):
    messages = turn['messages']
    return [(value(message), value(messages[index + 1]))
            for index, message in enumerate(messages) if message['role'] == 'assistant']


def cat(path, root):
    return {'tool': 'command', 'arguments': {'argv': ['cat', str(path)], 'cwd': str(root)}}


def test_actual_call_result_conversation_is_required_for_scripted_final(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'answer.txt'
    source.write_text('The observed value is 42.\n')
    actual_call = cat(source, root)
    def initial(turn):
        assert [m['role'] for m in turn['messages']] == ['system', 'user']
        assert value(turn['messages'][1])['question'] == 'Read the actual answer'
        assert 'observations' not in value(turn['messages'][1])
        return actual_call
    def require_conversation(turn):
        assert [m['role'] for m in turn['messages']] == ['system', 'user', 'assistant', 'user', 'user']
        pairs = calls_and_results(turn)
        assert len(pairs) == 1 and pairs[0][0] == actual_call
        packet = pairs[0][1]
        assert packet['packet_id'] == 'command-packet-1'
        assert packet['stdout'] == source.read_text()
        assert packet['source_reads'][0]['content_sha256'] == hashlib.sha256(source.read_bytes()).hexdigest()
        assert 'public_tool_call' not in packet
        assert 'Read the actual answer' not in turn['messages'][-1]['content']
        assert '"tool"' not in turn['messages'][-1]['content']
        assert value(turn['messages'][-1])['progress']['stage'] == 'continuation'
        assert 'observations' not in value(turn['messages'][1])
        return {'answer': '42', 'findings': [{'text': 'The observed value is 42.',
            'evidence_packets': [packet['packet_id']]}], 'unresolved_questions': []}
    backend = Backend([initial, require_conversation])
    result = worker(backend).run(request(question='Read the actual answer'))
    assert result['status'] == 'completed' and result['answer'] == '42'
    assert len(packets) == 1
    assert result['observations'][0]['public_tool_call'] == actual_call
    assert checkpoints[-1] == result['observations']
    assert backend.turns[0]['messages'][0] == backend.turns[1]['messages'][0]
    assert sum('The observed value is 42.' in m['content'] for m in backend.turns[1]['messages']) == 1


def test_checkpointed_call_ledger_replays_after_preemption_with_fresh_fence(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'resume.txt'
    source.write_text('public resumed fact\n')
    actual_call = cat(source, root)
    def resumed(turn):
        assert calls_and_results(turn)[0][0] == actual_call
        assert calls_and_results(turn)[0][1]['stdout'] == source.read_text()
        assert value(turn['messages'][-1])['progress']['stage'] == 'resumed'
        return final()
    backend = Backend([actual_call, resumed])
    backend.hook = lambda: setattr(backend, 'preempt', True)
    generation = [1]
    port = worker(backend, fence=lambda job, attempt: generation[0] == attempt)
    yielded = port.run(request(session_id='ledger-session'))
    assert yielded['status'] == 'yielding' and yielded['reason'] == 'foreground_preemption'
    assert yielded['observations'] == checkpoints[-1]
    generation[0], backend.preempt, backend.hook = 2, False, None
    stale = port.run(request(session_id='ledger-session', observations=yielded['observations']))
    assert stale['status'] == 'stale_attempt' and len(backend.turns) == 1
    result = port.run(request(attempt=2, session_id='ledger-session', observations=copy.deepcopy(checkpoints[-1])))
    assert result['status'] == 'completed' and result['observations'] == yielded['observations']
    assert len(packets) == 1


def test_legacy_observations_are_explicit_evidence_without_fabricated_calls(fixture):
    *_, worker = fixture
    legacy = {'packet_id': 'legacy-packet', 'stdout': 'public legacy fact'}
    def inspect(turn):
        assert not calls_and_results(turn)
        assert value(turn['messages'][2]) == {'retained_observation': legacy}
        assert value(turn['messages'][-1])['progress']['stage'] == 'resumed'
        assert 'observations' not in value(turn['messages'][1])
        return final()
    result = worker(Backend([inspect])).run(request(observations=[legacy]))
    assert result['status'] == 'completed' and result['observations'] == [legacy]


def test_missing_evidence_still_allows_another_actual_call(fixture):
    root, runner, packets, checkpoints, worker = fixture
    one, two = root / 'one.txt', root / 'two.txt'
    one.write_text('First fact, additional source needed.\n')
    two.write_text('Second fact completes the answer.\n')
    def missing(turn):
        assert calls_and_results(turn)[0][0] == cat(one, root)
        return cat(two, root)
    def complete(turn):
        assert [call for call, result in calls_and_results(turn)] == [cat(one, root), cat(two, root)]
        return final()
    result = worker(Backend([cat(one, root), missing, complete])).run(request())
    assert result['status'] == 'completed' and len(packets) == 2


def test_native_skill_entry_and_reference_calls_replay_before_selection(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry, reference = root / 'SKILL.md', root / 'native-reference.md'
    entry.write_text('Read native-reference.md as the next prerequisite.\n')
    reference.write_text('Actual selected native prerequisite.\n')
    def native_reference(turn):
        assert calls_and_results(turn)[0][0] == cat(entry, root)
        assert 'Read native-reference.md' in calls_and_results(turn)[0][1]['stdout']
        return cat(reference, root)
    def select(turn):
        assert [call for call, result in calls_and_results(turn)] == [cat(entry, root), cat(reference, root)]
        return final() | {'skill_selection': {'format': 'pc-skill-selection/1', 'synthesis': 'native selection',
            'selections': [{'skill': 'tiny', 'resource': 'native-reference.md', 'reason': 'native prerequisite',
                'content_sha256': hashlib.sha256(reference.read_bytes()).hexdigest(), 'line_start': 1, 'line_end': 1}]}}
    backend = Backend([example, native_reference, select])
    result = worker(backend).run(request(mode='skill', skill={'name': 'tiny', 'root': str(root)}))
    assert result['status'] == 'completed'
    assert result['observations'][0]['public_tool_call'] == cat(entry, root)
    assert result['observations'][1]['public_tool_call'] == cat(reference, root)
    assert 'public_tool_call' not in result['observations'][2]  # Internal validation is not a model call.
    assert sum(str(entry) == r['path'] for p in packets for r in p.get('source_reads', [])) == 1


def test_turn_between_60k_and_90k_retains_all_evidence(fixture):
    *_, worker = fixture
    observations = [{'packet_id': str(i), 'stdout': 'line\n' * 3000,
        'public_tool_call': {'tool': 'command', 'arguments': {'argv': ['printf', 'x' * 800], 'cwd': '/tmp'}}}
        for i in range(2)]
    refresh_context = {'prior_answer': 'retained historical context ' * 900}
    # This reproduces the former 60KB-only failure while remaining under the
    # verified 90KB turn contract.
    assert len(json.dumps(request(observations=observations, refresh_context=refresh_context)).encode()) < 96 * 1024
    backend = Backend([final()])
    result = worker(backend).run(request(observations=observations, refresh_context=refresh_context))
    assert result['status'] == 'completed'
    turn_bytes = len(json.dumps(backend.turns[0], ensure_ascii=False).encode())
    assert len(backend.turns) == 1 and 60000 < turn_bytes <= 90000
    assert result['observations'] == observations
    contents = [json.loads(m['content']) for m in backend.turns[0]['messages'] if m['role'] == 'user']
    allowed = next(item['progress']['allowed_observation_packet_ids'] for item in contents
                   if 'progress' in item and 'allowed_observation_packet_ids' in item['progress'])
    assert allowed == ['0', '1']
    assert not any('omitted_retained_observations' in item for item in contents)


def test_over_90k_turn_omits_oldest_complete_frames_truthfully(fixture):
    *_, worker = fixture
    observations = [{'packet_id': str(i), 'stdout': 'line\n' * 4500,
        'public_tool_call': {'tool': 'command', 'arguments': {'argv': ['printf', 'x' * 800], 'cwd': '/tmp'}}}
        for i in range(2)]
    refresh_context = {'prior_answer': 'retained historical context ' * 900}
    assert len(json.dumps(request(observations=observations, refresh_context=refresh_context)).encode()) < 96 * 1024
    omitted_for_test = []
    def cite_omitted(turn):
        values = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
        progress = next(item['progress'] for item in values if 'progress' in item
                        and 'omitted_observation_packet_ids' in item['progress'])
        omitted = progress['omitted_observation_packet_ids']
        assert omitted and omitted[0] not in progress['allowed_observation_packet_ids']
        omitted_for_test.append(omitted[0])
        return final() | {'findings': [{'text': 'unseen fact', 'evidence_packets': [omitted[0]]}]}
    def correct(turn):
        values = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
        rejected = next(item['retained_observation'] for item in values
                        if isinstance(item, dict) and isinstance(item.get('retained_observation'), dict)
                        and item['retained_observation'].get('reason') == 'investigate_final_validation_failed')
        allowed = rejected['validation_data']['allowed_observation_packet_ids']
        assert rejected['failure_classification'] == 'finding_requires_observed_packet'
        assert omitted_for_test[0] not in allowed
        return final() | {'answer': 'omitted citation rejected'}
    backend = Backend([cite_omitted, correct])
    result = worker(backend).run(request(observations=observations, refresh_context=refresh_context, max_steps=3))
    assert result['status'] == 'completed' and result['answer'] == 'omitted citation rejected'
    assert result['observations'][:2] == observations
    turn = backend.turns[0]
    assert len(json.dumps(turn, ensure_ascii=False).encode()) <= runtime.MODEL_TURN_MAX_BYTES
    assert len(turn['messages']) <= runtime.MODEL_TURN_MAX_MESSAGES
    contents = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
    omission = next(item['omitted_retained_observations'] for item in contents
                    if 'omitted_retained_observations' in item)
    allowed = next(item['progress']['allowed_observation_packet_ids'] for item in contents
                   if 'progress' in item and 'allowed_observation_packet_ids' in item['progress'])
    assert omission['count'] > 0 and omission['is_source_evidence'] is False
    assert len(allowed) + omission['count'] == len(observations)
    assert set(allowed).isdisjoint(omission['packet_ids'])


def test_message_count_cap_prunes_whole_call_result_pairs(fixture):
    *_, worker = fixture
    observations = [{'packet_id': f'packet-{i}', 'stdout': f'fact-{i}',
        'public_tool_call': {'tool': 'command', 'arguments': {'argv': ['pwd'], 'cwd': '/tmp'}}}
        for i in range(24)]
    backend = Backend([final()])
    result = worker(backend).run(request(observations=observations))
    assert result['status'] == 'completed' and result['observations'] == observations
    turn = backend.turns[0]
    assert len(turn['messages']) <= 24
    messages = turn['messages']
    omission = next(json.loads(m['content'])['omitted_retained_observations'] for m in messages
                    if m['role'] == 'user' and 'omitted_retained_observations' in json.loads(m['content']))
    visible_calls = sum(m['role'] == 'assistant' for m in messages)
    assert visible_calls + omission['count'] == len(observations)


def test_oversized_checkpoint_uses_ordered_frame_subset_without_mutating_result(fixture):
    root, runner, packets, checkpoints, worker = fixture
    observations = [{'packet_id': f'prior-{i}', 'stdout': 'x' * 25000}
                    for i in range(4)]
    call = {'tool': 'search', 'arguments': {'query': 'add a bounded observation'}}
    backend = Backend([call, final()])
    port = runtime.ObserverWorkerPort(backend, command=runner,
        tools=lambda name, args: {'packet_id': 'semantic-packet', 'status': 'ok'},
        fence=lambda job, attempt: True,
        checkpoint=lambda job, attempt, frames: checkpoints.append(copy.deepcopy(frames)))
    # The request plus metadata exceeds 96KiB, the service input ceiling is
    # larger, and the per-callback checkpoint still gets an ordered bounded suffix.
    job = request(observations=observations, max_steps=3)
    job_bytes = len(json.dumps(job, ensure_ascii=False).encode())
    assert runtime.CHECKPOINT_MAX_BYTES < job_bytes < runtime.JOB_INPUT_MAX_BYTES
    result = port.run(job)
    assert result['status'] == 'completed'
    assert [item['packet_id'] for item in result['observations'][:4]] == [f'prior-{i}' for i in range(4)]
    assert result['observations'][-1]['packet_id'] == 'semantic-packet'
    checkpoint = checkpoints[-1]
    assert len(json.dumps(checkpoint, ensure_ascii=False).encode()) <= runtime.CHECKPOINT_MAX_BYTES
    assert len(json.dumps(backend.turns[0], ensure_ascii=False).encode()) <= runtime.MODEL_TURN_MAX_BYTES
    assert checkpoint == result['observations'][-len(checkpoint):]
    assert all(item in result['observations'] for item in checkpoint)


def test_oversized_result_omission_preserves_exact_accepted_call(fixture):
    root, runner, packets, checkpoints, worker = fixture
    call = {'tool': 'command', 'arguments': {'argv': ['/usr/bin/python3', '-c', 'print("x" * 40000)'],
        'cwd': str(root), 'max_output_bytes': 45000}}
    result = worker(Backend([call, final()])).run(request(max_steps=2))
    observation = result['observations'][0]
    assert result['status'] == 'completed'
    assert observation['public_tool_call'] == call and observation['packet_id']
    assert 'stdout' not in observation and observation['omissions']
    assert len(json.dumps(observation).encode()) <= 32768
    assert checkpoints[-1] == result['observations']


@pytest.mark.parametrize('bad', [json.dumps(final()) + '\n' + json.dumps(final()),
                               '```json\n' + json.dumps(final()) + '\n```'])
def test_replay_keeps_strict_single_json_and_retained_call(fixture, bad):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'strict.txt'
    source.write_text('strict source\n')
    call = cat(source, root)
    def repaired(turn):
        values = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
        assert any(item.get('protocol_error') == 'invalid_json_object' for item in values)
        assert calls_and_results(turn)[0][0] == call
        return final() | {'answer': 'repaired after strict parse failure',
            'findings': [{'text': 'strict source retained', 'evidence_packets': ['command-packet-1']}]}
    result = worker(Backend([call, bad, repaired])).run(request())
    assert result['status'] == 'completed' and result['answer'] == 'repaired after strict parse failure'
    assert 'strict source retained' not in json.dumps(result['observations'])
    assert result['observations'][0]['public_tool_call'] == call
    assert len(packets) == 1


def test_stale_turn_never_adds_call_metadata_or_checkpoint(fixture):
    root, runner, packets, checkpoints, worker = fixture
    generation = [1]
    backend = Backend([example])
    backend.hook = lambda: generation.__setitem__(0, 2)
    result = worker(backend, fence=lambda job, attempt: generation[0] == attempt).run(request())
    assert result['status'] == 'stale_attempt' and not packets and not checkpoints


def test_retained_call_metadata_rejects_unavailable_tools(fixture):
    *_, worker = fixture
    backend = Backend([final()])
    result = worker(backend).run(request(observations=[{'packet_id': 'retained',
        'public_tool_call': {'tool': 'finish_task', 'arguments': {}}}]))
    assert result['status'] == 'partial' and result['reason'] == 'invalid_retained_public_tool_call'
    assert not backend.turns


def test_argument_mutation_by_adapter_cannot_rewrite_accepted_public_call(fixture):
    from local_worker.observer_runtime import ObserverWorkerPort
    root, runner, packets, checkpoints, worker = fixture
    actual_call = {'tool': 'search', 'arguments': {'query': 'actual accepted query'}}
    def adapter(tool, arguments):
        assert tool == 'search'
        arguments['query'] = 'adapter changed query'
        return {'packet_id': 'semantic-packet', 'status': 'ok'}
    backend = Backend([actual_call, final()])
    port = ObserverWorkerPort(backend, command=runner, tools=adapter, fence=lambda job, attempt: True,
        checkpoint=lambda job, attempt, observations: checkpoints.append(copy.deepcopy(observations)))
    result = port.run(request())
    assert result['status'] == 'completed'
    assert result['observations'][0]['public_tool_call'] == actual_call
    assert calls_and_results(backend.turns[1])[0][0] == actual_call


@pytest.mark.parametrize('bad,classification', [
    ({'answer': 'unaccepted answer', 'findings': [{'text': 'unsupported',
      'evidence_packets': ['nested-source-packet']}], 'unresolved_questions': []}, 'finding_requires_observed_packet'),
    ({'answer': '', 'findings': [], 'unresolved_questions': []}, 'final_answer_missing'),
    ({'answer': 'unaccepted answer', 'findings': [], 'unresolved_questions': 'not-a-list'}, 'invalid_unresolved_questions'),
])
def test_investigate_final_validation_feedback_is_safe_and_correctable(fixture, bad, classification):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'answer.txt'
    source.write_text('outer broker observation supports the corrected answer\n')
    call = cat(source, root)
    correct = {'answer': 'corrected answer', 'findings': [{'text': 'supported fact',
        'evidence_packets': ['command-packet-1']}], 'unresolved_questions': []}
    def correct_final(turn):
        messages = turn['messages']
        feedback = [json.loads(m['content']) for m in messages if m['role'] == 'user']
        rejected = next(item['retained_observation'] for item in feedback
                        if isinstance(item, dict) and isinstance(item.get('retained_observation'), dict)
                        and item['retained_observation'].get('reason') == 'investigate_final_validation_failed')
        assert rejected['failure_classification'] == classification
        assert rejected['validation_data']['is_source_evidence'] is False
        assert rejected['validation_data']['allowed_observation_packet_ids'] == ['command-packet-1']
        assert rejected['corrective_action'].find('nested source/tool packet references') >= 0
        assert rejected['accepted'] is False and 'proposed_final' not in rejected['validation_data']
        allowed = next(item['progress']['allowed_observation_packet_ids'] for item in feedback
                       if isinstance(item, dict) and 'progress' in item and 'allowed_observation_packet_ids' in item['progress'])
        assert allowed == ['command-packet-1']
        assert 'nested-source-packet' not in json.dumps(messages)
        return correct
    backend = Backend([call, bad, correct_final])
    result = worker(backend).run(request(max_steps=3))
    assert result['status'] == 'completed' and result['answer'] == 'corrected answer'
    assert result['findings'] == correct['findings'] and result['unresolved_questions'] == []
    assert [o['reason'] for o in result['observations'] if o.get('reason')]
    assert len(backend.turns) == 3 and len(packets) == 2
    rejection = result['observations'][1]
    assert rejection['failure_classification'] == classification
    assert 'unaccepted answer' not in json.dumps(result['observations'])


def test_investigate_final_validation_exhaustion_retains_safe_classification(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'answer.txt'
    source.write_text('visible fact\n')
    call = cat(source, root)
    invalid = {'answer': 'bad', 'findings': [{'text': 'bad cite', 'evidence_packets': ['nested']}],
               'unresolved_questions': []}
    result = worker(Backend([call, invalid, invalid])).run(request(max_steps=3))
    assert result['status'] == 'partial' and result['reason'] == 'finding_requires_observed_packet'
    assert result['failure_classification'] == 'finding_requires_observed_packet'
    assert 'answer' not in result and result['findings'] == []
    assert len(result['observations']) == 2
    assert result['observations'][-1]['failure_classification'] == 'finding_requires_observed_packet'


def test_strict_extra_json_data_is_repaired_without_dispatch(fixture):
    *_, worker = fixture
    def repaired(turn):
        user_values = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
        feedback = next(item for item in user_values if item.get('protocol_error') == 'invalid_json_object')
        assert 'Extra data' in feedback['detail']
        assert 'No tool call was dispatched' in feedback['instruction']
        assert not any(m['role'] == 'assistant' for m in turn['messages'])
        return {'answer': 'repaired', 'findings': [], 'unresolved_questions': []}
    backend = Backend(['{} {}', repaired])
    result = worker(backend).run(request(max_steps=3))
    assert result['status'] == 'completed' and result['answer'] == 'repaired'
    assert result['observations'] == [] and len(backend.turns) == 2
    assert 'context_budget' not in json.dumps(backend.turns)


def test_malformed_parsed_tool_envelope_is_repaired_without_dispatch(fixture):
    *_, worker = fixture
    def repaired(turn):
        values = [json.loads(m['content']) for m in turn['messages'] if m['role'] == 'user']
        assert any(item.get('protocol_error') == 'malformed_tool_envelope' for item in values)
        assert not any(m['role'] == 'assistant' for m in turn['messages'])
        return {'answer': 'repaired envelope', 'findings': [], 'unresolved_questions': []}
    result = worker(Backend([{'tool': [], 'arguments': {}}, repaired])).run(request(max_steps=2))
    assert result['status'] == 'completed' and result['answer'] == 'repaired envelope'
    assert result['observations'] == []


def test_successful_investigate_result_assembles_validated_final_and_observations(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'assembled.txt'
    source.write_text('assembled fact\n')
    call = cat(source, root)
    valid = {'answer': 'assembled answer', 'findings': [{'text': 'assembled fact',
        'evidence_packets': ['command-packet-1']}], 'unresolved_questions': []}
    result = worker(Backend([call, valid])).run(request(max_steps=3))
    assert result['status'] == 'completed' and result['authoritative'] is False
    assert result['answer'] == valid['answer'] and result['findings'] == valid['findings']
    assert result['unresolved_questions'] == [] and result['observations'][0]['packet_id'] == 'command-packet-1'
    assert checkpoints[-1] == result['observations']
    assert checkpoints[-1] == result['observations']
