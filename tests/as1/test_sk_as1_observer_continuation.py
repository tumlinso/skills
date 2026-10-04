"""Stage-aware actual-port fixtures; scripted turns do not qualify inference."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sk_as1_observer_progress import Backend, example, final, fixture, request


def context(turn):
    messages = turn['messages']
    initial = json.loads(messages[1]['content'])
    observations = []
    for index, message in enumerate(messages[2:], 2):
        value = json.loads(message['content'])
        if message['role'] == 'user' and 'packet_id' in value:
            observations.append({**value, 'public_tool_call': json.loads(messages[index - 1]['content'])})
        elif message['role'] == 'user' and 'retained_observation' in value:
            observations.append(value['retained_observation'])
    progress = json.loads(messages[-1]['content']).get('progress', initial.get('progress'))
    return {**{key: value for key, value in initial.items() if key not in {'progress', 'instruction'}},
            'observations': observations, 'progress': progress}


def test_initial_cat_then_continuation_can_finish_without_source_reread(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'answer.txt'
    source.write_text('The public source value is 42.\n')
    def initial(turn):
        assert context(turn)['progress'] == {'stage': 'initial', 'observation_count': 0, 'remaining_steps': 6}
        assert 'Start with command for source/files/Git relevant' in turn['messages'][1]['content']
        return {'tool': 'command', 'arguments': {'argv': ['cat', str(source)], 'cwd': str(root)}}
    def continuation(turn):
        public = context(turn)
        assert public['progress'] == {'stage': 'continuation', 'observation_count': 1, 'remaining_steps': 5}
        instruction = turn['messages'][0]['content']
        assert 'Start with command' not in instruction
        assert 'If sufficient, return final JSON now' in instruction
        assert 'only to obtain missing evidence' in instruction
        assert public['observations'][0]['stdout'] == source.read_text()
        assert public['observations'][0]['source_reads'][0]['path'] == str(source)
        return {'answer': '42', 'findings': [{'text': 'The public source value is 42.',
            'evidence_packets': [public['observations'][0]['packet_id']]}], 'unresolved_questions': []}
    backend = Backend([initial, continuation])
    result = worker(backend).run(request())
    assert result['status'] == 'completed'
    assert len(packets) == len(checkpoints) == 1
    assert len(backend.turns) == 2 and result['answer'] == '42'
    assert set(context(backend.turns[1])) == {'question', 'observations', 'progress'}


def test_retained_public_source_survives_preemption_and_resumes_directly_to_final(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'resume.txt'
    source.write_text('retained public source\n')
    retained = [runner.run(['cat', str(source)], cwd=str(root))]
    retained_copy = copy.deepcopy(retained)
    def resumed(turn):
        assert context(turn)['progress']['stage'] == 'resumed'
        assert context(turn)['observations'] == retained_copy
        assert 'Start with command' not in turn['messages'][0]['content']
        return final()
    backend = Backend([resumed])
    backend.preempt = True
    generation = [1]
    port = worker(backend, fence=lambda job, attempt: attempt == generation[0])
    yielded = port.run(request(session_id='continuation-session', observations=retained))
    assert yielded['status'] == 'yielding' and yielded['reason'] == 'foreground_preemption'
    assert not backend.turns
    generation[0], backend.preempt = 2, False
    stale = port.run(request(session_id='continuation-session', observations=retained))
    assert stale['status'] == 'stale_attempt' and not backend.turns
    result = port.run(request(attempt=2, session_id='continuation-session', observations=yielded['observations']))
    assert result['status'] == 'completed' and result['observations'] == retained_copy
    assert len(packets) == 1 and not checkpoints
    assert retained == retained_copy


def test_incomplete_retained_evidence_can_still_request_missing_source(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'missing.txt'
    source.write_text('newly observed missing evidence\n')
    def missing(turn):
        assert context(turn)['progress']['stage'] == 'resumed'
        assert 'incomplete, stale' in turn['messages'][0]['content']
        return {'tool': 'command', 'arguments': {'argv': ['cat', str(source)], 'cwd': str(root)}}
    backend = Backend([missing, final()])
    result = worker(backend).run(request(observations=[{'packet_id': 'incomplete-packet',
        'omissions': ['Decisive source was not read']}]))
    assert result['status'] == 'completed'
    assert len(packets) == 1 and len(result['observations']) == 2


def test_skill_initial_example_reads_exact_entry_then_follows_native_maps(fixture):
    root, runner, packets, checkpoints, worker = fixture
    entry = root / 'SKILL.md'
    entry.write_text('Read refs/router.md for the native map.\n')
    refs = root / 'refs'
    refs.mkdir()
    router, selected = refs / 'router.md', refs / 'selected.md'
    router.write_text('Read selected.md before selecting.\n')
    selected.write_text('native selected prerequisite\n')
    def initial(turn):
        command = example(turn)
        assert command == {'tool': 'command', 'arguments': {'argv': ['cat', str(entry)], 'cwd': str(root)}}
        assert 'registered-root' not in turn['messages'][0]['content']
        assert 'max_output_bytes (integer 1..65536, default 8192)' in turn['messages'][0]['content']
        assert 'native map' not in turn['messages'][1]['content']
        return command
    def read_router(turn):
        assert context(turn)['progress']['stage'] == 'continuation'
        assert 'native map' in json.dumps(context(turn)['observations'])
        assert 'native map' not in turn['messages'][1]['content']
        assert 'follow its own maps and references agentically' in turn['messages'][0]['content']
        return {'tool': 'command', 'arguments': {'argv': ['cat', str(router)], 'cwd': str(root)}}
    def read_selected(turn):
        assert 'Read selected.md before selecting' in json.dumps(context(turn)['observations'])
        assert 'Read selected.md before selecting' not in turn['messages'][1]['content']
        return {'tool': 'command', 'arguments': {'argv': ['cat', str(selected)], 'cwd': str(root)}}
    selection = {'format': 'pc-skill-selection/1', 'synthesis': 'native selection',
        'selections': [{'skill': 'tiny', 'resource': 'refs/selected.md', 'reason': 'native prerequisite',
            'content_sha256': hashlib.sha256(selected.read_bytes()).hexdigest(), 'line_start': 1, 'line_end': 1}]}
    backend = Backend([initial, read_router, read_selected, final() | {'skill_selection': selection}])
    result = worker(backend).run(request(mode='skill', skill={'name': 'tiny', 'root': str(root)}))
    assert result['status'] == 'completed'
    reads = [read['path'] for packet in packets for read in packet.get('source_reads', [])]
    assert reads.count(str(entry)) == reads.count(str(router)) == 1
    assert reads.count(str(selected)) == 2  # Existing final source validation remains mandatory.
    assert len(backend.turns) == 4


@pytest.mark.parametrize('bad', [json.dumps(final()) + '\n' + json.dumps(final()),
                               '```json\n' + json.dumps(final()) + '\n```'])
def test_continuation_does_not_relax_single_json_parser(fixture, bad):
    *_, worker = fixture
    result = worker(Backend([bad])).run(request(observations=[{'packet_id': 'retained-public-packet'}]))
    assert result['status'] == 'partial' and 'answer' not in result
    assert result['observations'] == [{'packet_id': 'retained-public-packet'}]


def test_retained_observation_bound_stays_enforced(fixture):
    *_, worker = fixture
    backend = Backend([final()])
    with pytest.raises(ValueError, match='bounded evidence context'):
        worker(backend).run(request(observations=[{'packet_id': str(i)} for i in range(25)]))
    assert not backend.turns
