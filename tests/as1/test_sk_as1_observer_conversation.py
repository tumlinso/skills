"""Real-port public conversation tests; no inference or hidden reasoning fixture."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sk_as1_observer_progress import Backend, example, final, fixture, request


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


def test_total_message_request_budget_counts_history_and_system(fixture):
    *_, worker = fixture
    observations = [{'packet_id': str(i), 'stdout': 'x' * 14200,
        'public_tool_call': {'tool': 'command', 'arguments': {'argv': ['printf', 'x' * 1500], 'cwd': '/tmp'}}}
        for i in range(4)]
    # The input is <=65536 bytes; expanded roles/protocol still exceed 60000.
    assert len(json.dumps(request(observations=observations)).encode()) < 65536
    backend = Backend([final()])
    result = worker(backend).run(request(observations=observations))
    assert result['status'] == 'partial' and result['reason'] == 'context_budget'
    assert not backend.turns and result['observations'] == observations


def test_oversized_result_omission_preserves_exact_accepted_call(fixture):
    root, runner, packets, checkpoints, worker = fixture
    call = {'tool': 'command', 'arguments': {'argv': ['/usr/bin/python3', '-c', 'print("x" * 18000)'],
        'cwd': str(root), 'max_output_bytes': 20000}}
    result = worker(Backend([call])).run(request(max_steps=1))
    observation = result['observations'][0]
    assert result['reason'] == 'step_budget_exhausted'
    assert observation['public_tool_call'] == call and observation['packet_id']
    assert 'stdout' not in observation and observation['omissions']
    assert len(json.dumps(observation).encode()) <= 16384
    assert checkpoints[-1] == result['observations']


@pytest.mark.parametrize('bad', [json.dumps(final()) + '\n' + json.dumps(final()),
                               '```json\n' + json.dumps(final()) + '\n```'])
def test_replay_keeps_strict_single_json_and_retained_call(fixture, bad):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'strict.txt'
    source.write_text('strict source\n')
    call = cat(source, root)
    result = worker(Backend([call, bad])).run(request())
    assert result['status'] == 'partial' and 'answer' not in result
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
    assert checkpoints[-1] == result['observations']
