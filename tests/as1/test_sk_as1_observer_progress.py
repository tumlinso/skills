"""Installed source/Bubblewrap regressions; scripted turns are not model proof."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / 'local-coding-worker'))
import local_worker.observer_runtime as runtime

SOURCE = SKILLS / 'local-coding-worker/local_worker/observer_runtime.py'
BINDINGS = ('PROJECT_CONTROL_SKILLS_ROOT', 'CODING_WORKFLOW_SKILLS_ROOT',
            'CODING_WORKFLOW_RUNTIME_FINGERPRINT', 'PROJECT_CONTROL_RELEASE_MANIFEST',
            'PROJECT_CONTROL_RELEASE_DIGEST')


class Backend:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.turns = []
        self.preempt = False
        self.hook = None

    def preemption_status(self, session):
        return {'preempt_requested': self.preempt, 'draining': False}

    def run_observer_turn(self, turn):
        self.turns.append(copy.deepcopy(turn))
        reply = next(self.replies)
        if callable(reply):
            reply = reply(turn)
        if self.hook:
            self.hook()
        return {'status': 'available', 'text': reply if isinstance(reply, str) else json.dumps(reply)}


def final():
    return {'answer': 'fixture answer', 'findings': [], 'unresolved_questions': []}


def example(turn):
    instruction = turn['messages'][0]['content']
    text = instruction.split('Return exactly one JSON object only: ', 1)[1]
    return json.JSONDecoder().raw_decode(text)[0]


@pytest.fixture
def fixture(tmp_path):
    assert Path(runtime.__file__).resolve() == SOURCE
    if os.environ.get('AS1_PROGRESS_CHILD_SHA256'):
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == os.environ['AS1_PROGRESS_CHILD_SHA256']
    root = tmp_path / 'trusted root'
    root.mkdir()
    packets, checkpoints = [], []
    def packetize(payload):
        packets.append(copy.deepcopy(payload))
        return 'command-packet-' + str(len(packets))
    runner = runtime.ReadOnlyCommandRunner([root], packetize=packetize)
    def worker(backend, command=runner, fence=lambda job, attempt: True):
        return runtime.ObserverWorkerPort(backend, command=command,
            tools=lambda name, args: pytest.fail('unexpected semantic tool'), fence=fence,
            checkpoint=lambda job, attempt, observations: checkpoints.append(copy.deepcopy(observations)))
    return root, runner, packets, checkpoints, worker


def request(**extra):
    return {'job_id': 'progress-fixture', 'attempt': 1, 'mode': 'investigate',
            'question': 'Which native source resolves this question?', **extra}


def test_actual_prompt_command_executes_native_cwd_without_caller_root_grants(fixture, tmp_path):
    root, runner, packets, checkpoints, worker = fixture
    malicious = str(tmp_path / 'request-must-not-grant-this-root')
    backend = Backend([example, final()])
    result = worker(backend).run(request(scope=malicious, hints={'roots': [malicious], 'cwd': '/'}))
    instruction = backend.turns[0]['messages'][0]['content']
    command = example(backend.turns[0])
    assert command == {'tool': 'command', 'arguments': {'argv': ['pwd'], 'cwd': str(root)}}
    assert malicious not in instruction
    assert 'allowed path' not in instruction
    assert 'do not repeatedly copy the example command' in instruction
    assert result['status'] == 'completed'
    assert packets[0]['status'] == 'completed', packets[0]
    assert packets[0]['stdout'].strip() == str(root)
    assert checkpoints
    assert runner.run(['pwd'], cwd=malicious)['status'] == 'denied'


def test_no_root_adapter_example_omits_cwd_and_uses_adapter_default(fixture):
    *_, worker = fixture
    class HostDefaultAdapter:
        def run(self, argv, *, guard):
            assert guard() and argv == ['pwd']
            return {'packet_id': 'adapter-default', 'status': 'completed', 'stdout': os.getcwd()}
    backend = Backend([example, final()])
    result = worker(backend, command=HostDefaultAdapter()).run(request())
    assert 'cwd' not in example(backend.turns[0])['arguments']
    assert result['status'] == 'completed'


def test_native_root_order_keeps_deeper_project_first_and_deduplicates(fixture, tmp_path):
    *_, worker = fixture
    project = tmp_path / 'deep' / 'admitted-project'
    project.mkdir(parents=True)
    skills = tmp_path / 'skills'
    skills.mkdir()
    runner = runtime.ReadOnlyCommandRunner([project, skills, project / '.'],
        packetize=lambda payload: 'ordered-roots-packet')
    assert runner.roots == (project, skills)
    backend = Backend([example, final()])
    result = worker(backend, command=runner).run(request(scope=str(skills)))
    assert example(backend.turns[0])['arguments']['cwd'] == str(project)
    assert result['status'] == 'completed'
    assert result['observations'][0]['stdout'].strip() == str(project)


def test_six_command_turns_are_terminal_partial_with_retained_observations(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'source.txt'
    source.write_text('retained exact source\n')
    command = {'tool': 'command', 'arguments': {'argv': ['cat', str(source)], 'cwd': str(root)}}
    backend = Backend([command] * 6)
    result = worker(backend).run(request(observations=[{'packet_id': 'prior-packet'}]))
    assert result['status'] == 'partial'
    assert result['reason'] == 'step_budget_exhausted'
    assert result['authoritative'] is False
    assert result['unresolved_questions']
    assert 'what remains unverified' in result['unresolved_questions'][0]
    assert len(backend.turns) == len(packets) == len(checkpoints) == 6
    assert len(result['observations']) == 7
    assert result['observations'][0]['packet_id'] == 'prior-packet'
    assert checkpoints[-1] == result['observations']
    assert all(observation['source_reads'] for observation in result['observations'][1:])
    assert result['status'] not in {'yielding', 'queued_after_eviction'}
    assert 'answer' not in result


def test_foreground_yield_resumes_retained_source_with_fresh_attempt(fixture):
    root, runner, packets, checkpoints, worker = fixture
    source = root / 'source.txt'
    source.write_text('source survives foreground preemption\n')
    backend = Backend([{'tool': 'command', 'arguments': {'argv': ['cat', str(source)], 'cwd': str(root)}}, final()])
    backend.hook = lambda: setattr(backend, 'preempt', True)
    generation = [1]
    port = worker(backend, fence=lambda job, attempt: attempt == generation[0])
    yielded = port.run(request(session_id='fixture-session'))
    assert yielded['status'] == 'yielding' and yielded['reason'] == 'foreground_preemption'
    assert len(yielded['observations']) == 1 and checkpoints
    backend.preempt, backend.hook = False, None
    generation[0] = 2
    stale = port.run(request(session_id='fixture-session', observations=yielded['observations']))
    assert stale['status'] == 'stale_attempt'
    assert len(backend.turns) == 1
    resumed = port.run(request(attempt=2, session_id='fixture-session', observations=yielded['observations']))
    assert resumed['status'] == 'completed'
    assert resumed['observations'] == yielded['observations']
    assert 'source survives foreground preemption' in backend.turns[-1]['messages'][1]['content']


def test_superseded_turn_cannot_publish_a_command(fixture):
    root, runner, packets, checkpoints, worker = fixture
    generation = [1]
    backend = Backend([example])
    backend.hook = lambda: generation.__setitem__(0, 2)
    result = worker(backend, fence=lambda job, attempt: attempt == generation[0]).run(request())
    assert result['status'] == 'stale_attempt'
    assert not packets and not checkpoints


@pytest.mark.parametrize('output', [json.dumps(final()) + '\n' + json.dumps(final()),
                                    '```json\n' + json.dumps(final()) + '\n```'])
def test_multi_json_and_fences_remain_rejected(fixture, output):
    root, runner, packets, checkpoints, worker = fixture
    result = worker(Backend([output])).run(request())
    assert result['status'] == 'partial'
    assert 'answer' not in result
    assert result['unresolved_questions'] and not packets and not checkpoints


def test_eviction_retains_recoverable_state(fixture):
    *_, worker = fixture
    class Evicted:
        def run_observer_turn(self, turn):
            return {'status': 'unavailable', 'reason': 'observer_session_unavailable'}
    retained = [{'packet_id': 'retained-packet'}]
    result = worker(Evicted()).run(request(observations=retained))
    assert result['status'] == 'queued_after_eviction'
    assert result['observations'] == retained


def test_source_bound_child_clears_deployment_pins_and_imports_exact_new_module():
    inherited = {key: os.environ.get(key) for key in BINDINGS}
    environment = dict(os.environ)
    for key in BINDINGS:
        environment.pop(key, None)
    environment.update(PROJECT_CONTROL_SKILLS_ROOT=str(SKILLS), CODING_WORKFLOW_SKILLS_ROOT=str(SKILLS),
        AS1_PROGRESS_CHILD_SHA256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        PYTHONPATH=str(SKILLS / 'local-coding-worker'))
    result = subprocess.run([sys.executable, '-m', 'pytest', str(Path(__file__).resolve()),
        '-q', '-k', 'not source_bound_child'], cwd=SKILLS, env=environment,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '9 passed' in result.stdout, result.stdout
    assert {key: os.environ.get(key) for key in BINDINGS} == inherited
