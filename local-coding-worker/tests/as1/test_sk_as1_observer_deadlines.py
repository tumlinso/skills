"""CPU deadlines: owned startup and active inference, with no GPU/model download."""
import json
import sys
import tempfile
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "local-coding-worker"))
from local_worker.observer_runtime import ObserverWorkerPort, ReadOnlyCommandRunner
from local_worker.servers.llama_cpp import LlamaCppServerAdapter
from local_worker.service import AdapterError


class Process:
    pid = 424242
    def __init__(self):
        self.returncode = None
    def poll(self):
        return self.returncode
    def wait(self, timeout=None):
        assert self.returncode is not None
        return self.returncode


def adapter_fixture(tmp_path, transport):
    binary = tmp_path / "server"
    binary.write_text("#!/bin/sh\n")
    binary.chmod(0o755)
    model = tmp_path / "fixture.gguf"
    model.write_bytes(b"GGUFfixture")
    processes, killed = [], []
    def spawn(*args, **kwargs):
        process = Process()
        processes.append(process)
        return process
    def stop(identity):
        killed.append(identity["pid"])
        processes[0].returncode = -9
    adapter = LlamaCppServerAdapter(str(binary), process_factory=spawn,
        transport=transport, help_runner=lambda *a, **kw: SimpleNamespace(stdout="", stderr=""),
        identity_reader=lambda pid: {"pid": pid}, owned_terminator=stop)
    return adapter, model, processes, killed


def test_startup_lifetime_stops_only_owned_process(tmp_path):
    adapter, model, processes, killed = adapter_fixture(tmp_path, lambda *a: (503, {}))
    started = time.monotonic()
    with pytest.raises(AdapterError, match="startup"):
        adapter.start({"model_path": str(model), "startup_timeout_seconds": 600,
                       "deadline_epoch": time.time() + .06})
    assert time.monotonic() - started < .5
    assert killed == [424242]
    assert processes[0].poll() is not None
    assert all(server["evicted"] for server in adapter._servers.values())


def test_inference_timeout_waits_for_transport_and_stops_owned_operation(tmp_path):
    stopped = threading.Event()
    transport_finished = threading.Event()
    calls = []
    def transport(method, url, body, timeout):
        if method == "GET":
            return 200, {}
        calls.append(timeout)
        assert stopped.wait(1), "hard bound did not stop owned operation"
        time.sleep(.02)  # Dispatch must retain its slot until this finishes.
        transport_finished.set()
        return 200, {"choices": [{"message": {"content": "{}"}}]}
    adapter, model, processes, killed = adapter_fixture(tmp_path, transport)
    original_stop = adapter.owned_terminator
    def stop(identity):
        original_stop(identity)
        stopped.set()
    adapter.owned_terminator = stop
    handle = adapter.start({"model_path": str(model)})
    # A distinct idle server remains untouched.
    adapter._servers["other"] = {"evicted": False, "accepting": True}
    with pytest.raises(AdapterError, match="timed_out"):
        adapter.run(handle, {"messages": [{"role": "user", "content": "question"}],
                    "timeout_seconds": .04, "deadline_epoch": time.time() + 1})
    assert transport_finished.is_set()
    assert 0 < calls[0] <= .04
    assert killed == [424242]
    assert not adapter._servers["other"]["evicted"]


def test_expired_deadline_does_not_dispatch_model_or_command(tmp_path):
    class Backend:
        def run_observer_turn(self, request):
            pytest.fail("expired inquiry dispatched a model")
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: "packet")
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: None, fence=lambda *a: True)
    with pytest.raises(TimeoutError):
        worker.run({"job_id": "job", "attempt": 1, "mode": "investigate", "question": "q",
                    "deadline_epoch": time.time() - 1})
    with pytest.raises(TimeoutError):
        runner.run(["cat", "x"], str(tmp_path), deadline_epoch=time.time() - 1)


def test_refresh_context_and_remaining_model_budget_are_forwarded(tmp_path):
    turns = []
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            return {"status": "available", "text": json.dumps({"answer": "prior answer", "findings": []})}
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: "packet")
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: None, fence=lambda *a: True)
    refresh = {"prior_answer": "prior answer", "findings": [], "changed_sources": ["file.py"]}
    deadline = time.time() + 5
    result = worker.run({"job_id": "job", "attempt": 1, "mode": "investigate", "question": "q",
                        "deadline_epoch": deadline, "refresh_context": refresh})
    assert result["status"] == "completed"
    assert turns[0]["deadline_epoch"] == deadline
    assert 0 < turns[0]["timeout_seconds"] <= 5
    assert json.loads(turns[0]["messages"][1]["content"])["refresh_context"] == refresh
    assert "Reuse valid prior work" in turns[0]["messages"][0]["content"]


def test_command_deadline_kills_cpu_process_group(tmp_path):
    import shutil
    if not shutil.which("bwrap"):
        pytest.skip("Bubblewrap unavailable")
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: "packet")
    started = time.monotonic()
    result = runner.run(["sleep", "2"], str(tmp_path), timeout_seconds=60,
                        deadline_epoch=time.time() + .06)
    if not result["timed_out"] and result.get("exit_code") != 0:
        pytest.skip("Host does not permit Bubblewrap namespace")
    assert result["timed_out"]
    assert time.monotonic() - started < .5


def test_supervisor_deadline_reaches_cold_start_and_transport(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "local-coding-worker/tests"))
    from test_supervisor import _PoolBackend, _Runtime, _Service, _Adapter, _Cache, _profile
    service = _Service()
    backend = _PoolBackend(tmp_path, runtime=_Runtime(), service=service, adapter=_Adapter(),
                           cache=_Cache(), profile=_profile(),
                           topology_classifier=lambda: SimpleNamespace(mode="x_mode", status="available"))
    backend._version = lambda binary, deadline_epoch=None: "fixture"
    deadline = time.time() + 5
    opened = backend.open_observer_sessions(1, compute_profile="narrow", parallelism="default",
                                             deadline_epoch=deadline)
    assert service.contexts[0]["deadline_epoch"] == deadline
    session = opened["session_ids"][0]
    result = backend.run_observer_turn({"format": "PC-LOCAL-INVESTIGATOR-TURN/2",
        "messages": [{"role": "user", "content": "q"}], "max_tokens": 20,
        "timeout_seconds": 90, "compute_profile": "narrow", "parallelism": "default",
        "session_id": session, "deadline_epoch": deadline})
    assert result["status"] == "available"
    assert service.requests[0][2]["deadline_epoch"] == deadline
    assert service.requests[0][2]["timeout_seconds"] <= 5
    backend.close_observer_session(session)
    backend.close()


def test_version_probe_timeout_releases_consumed_admission(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "local-coding-worker/tests"))
    from test_supervisor import _PoolBackend, _Runtime, _Service, _Adapter, _Cache, _profile
    runtime, service = _Runtime(), _Service()
    backend = _PoolBackend(tmp_path, runtime=runtime, service=service, adapter=_Adapter(),
        cache=_Cache(), profile=_profile(),
        topology_classifier=lambda: SimpleNamespace(mode="x_mode", status="available"))
    def expired_version(*args):
        raise TimeoutError("version_probe_deadline")
    backend._version = expired_version
    with pytest.raises(TimeoutError):
        backend.open_observer_sessions(1, compute_profile="narrow", parallelism="default",
                                        deadline_epoch=time.time() + 5)
    assert not runtime.host.owners
    assert not backend._admissions
    assert not backend._leases
    assert not service.starts


def test_failed_owned_cleanup_keeps_session_resolvable_until_retry(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "local-coding-worker/tests"))
    from test_supervisor import _PoolBackend, _Runtime, _Service, _Adapter, _Cache, _profile
    from local_worker.supervisor import SupervisorError
    runtime, service = _Runtime(), _Service()
    backend = _PoolBackend(tmp_path, runtime=runtime, service=service, adapter=_Adapter(),
        cache=_Cache(), profile=_profile(),
        topology_classifier=lambda: SimpleNamespace(mode="x_mode", status="available"))
    lease = backend.warm()
    session, slot_id = lease["service_lease_id"], lease["slot_id"]
    slot = backend._slots[slot_id]
    slot.state = "draining"
    original_evict = service.evict
    def failed_evict(*args):
        raise AdapterError("model_process_not_quiescent")
    service.evict = failed_evict
    with pytest.raises(SupervisorError, match="cleanup_pending"):
        backend.close_observer_session(session)
    assert backend._leases[session] == slot_id
    assert slot.service_lease_id == session
    assert slot.owner_id in runtime.host.owners
    service.evict = original_evict
    assert backend.close_observer_session(session)["released"]
    assert session not in backend._leases and slot_id not in backend._slots
    assert slot.owner_id not in runtime.host.owners


def test_active_turn_cannot_release_dispatch_session(tmp_path):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "local-coding-worker/tests"))
    from test_supervisor import ServicePoolTests
    from local_worker.supervisor import SupervisorError
    backend, runtime, service = ServicePoolTests().backend()
    lease = backend.warm()
    slot = backend._slots[lease["slot_id"]]
    slot.active_turns = 1
    with pytest.raises(SupervisorError, match="still active"):
        backend.close_observer_session(lease["service_lease_id"])
    assert slot.service_lease_id == lease["service_lease_id"]
    slot.active_turns = 0
    backend.close_observer_session(lease["service_lease_id"])
    backend.close()


def test_project_and_installed_skill_readmes_are_labeled_separately(tmp_path):
    project_root, skills_root = tmp_path / 'project', tmp_path / 'skills'
    project_root.mkdir()
    skills_root.mkdir()
    (project_root / 'README.md').write_text('Project interval: 17 seconds.')
    (skills_root / 'README.md').write_text('Installed skill integration guide.')
    turns = []
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            return {'status': 'available', 'text': json.dumps({'answer': 'context inspected', 'findings': []})}
    # Reverse root order proves project targeting does not rely on mount order.
    runner = ReadOnlyCommandRunner([skills_root, project_root], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: None, fence=lambda *a: True)
    repositories = [{'project': 'p', 'repository': 'main', 'root': str(project_root)}]
    worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate',
        'question': 'What interval does the project README document?',
        'inquiry_repositories': repositories, 'installed_skill_roots': [str(skills_root)]})
    context = json.loads(turns[0]['messages'][1]['content'])
    instruction = turns[0]['messages'][0]['content']
    assert context['inquiry_repositories'] == repositories
    assert context['installed_skill_roots'] == [str(skills_root)]
    assert 'broker-selected authoritative question targets' in instruction
    assert 'a similarly named file under an installed skill root is not project evidence' in instruction
    command_grammar = json.dumps({'tool': 'command', 'arguments': {'argv': ['pwd'], 'cwd': str(project_root)}})
    assert command_grammar in instruction
    assert '17 seconds' not in instruction  # Context labels do not manufacture source evidence.


def test_repository_labels_do_not_grant_unmounted_source_access(tmp_path):
    mounted, outside = tmp_path / 'mounted', tmp_path / 'outside'
    mounted.mkdir()
    outside.mkdir()
    turns = []
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            return {'status': 'available', 'text': json.dumps({'answer': 'context inspected', 'findings': []})}
    runner = ReadOnlyCommandRunner([mounted], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: None, fence=lambda *a: True)
    worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate', 'question': 'Inspect source',
        'inquiry_repositories': [{'project': 'p', 'repository': 'main', 'root': str(outside)}],
        'installed_skill_roots': [str(outside)]})
    assert not runner.allows(outside)
    assert json.dumps({'tool': 'command', 'arguments': {'argv': ['pwd'], 'cwd': str(mounted)}}) in turns[0]['messages'][0]['content']


@pytest.mark.parametrize('last_is_tool', [False, True])
def test_final_model_round_synthesizes_or_refuses_more_tools(tmp_path, last_is_tool):
    turns, calls = [], []
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            if len(turns) <= 5 or last_is_tool:
                value = {'tool': 'search', 'arguments': {'query': 'missing evidence'}}
            else:
                value = {'answer': 'Observed sources support a partial answer.',
                    'findings': [{'text': 'Observed source fact', 'evidence_packets': ['packet-1']}],
                    'unresolved_questions': ['One source remains unverified.']}
            return {'status': 'available', 'text': json.dumps(value)}
    def tools(name, arguments):
        calls.append((name, arguments))
        return {'packet_id': f'packet-{len(calls)}', 'source': 'observed source fact'}
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=tools, fence=lambda *a: True)
    deadline = time.time() + 5
    result = worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate',
        'question': 'What do the observed sources establish?', 'max_steps': 6, 'deadline_epoch': deadline})
    assert len(turns) == 6
    assert len(calls) == 5
    assert result['status'] == 'partial'
    last_context = json.loads(turns[-1]['messages'][-1]['content'])
    assert last_context['final_round'] is True
    assert 'Return final JSON only' in last_context['instruction']
    assert all(turn['deadline_epoch'] == deadline and 0 < turn['timeout_seconds'] <= 5 for turn in turns)
    if last_is_tool:
        assert result['reason'] == 'final_round_requires_answer'
        assert 'answer' not in result
    else:
        assert result['answer'] == 'Observed sources support a partial answer.'
        assert result['findings'][0]['evidence_packets'] == ['packet-1']
        assert result['unresolved_questions'] == ['One source remains unverified.']


def test_skill_final_round_reuses_agentically_read_maps_and_validates_source(tmp_path):
    import hashlib
    files = ['SKILL.md', 'map.md', 'architecture.md', 'start.md', 'needs.md']
    for index, name in enumerate(files):
        next_file = files[index + 1] if index + 1 < len(files) else 'none'
        (tmp_path / name).write_text(f'Read {next_file}; observed guidance {index}.\n')
    turns, reads = [], []
    class Command(ReadOnlyCommandRunner):
        def run(self, argv, cwd, **kwargs):
            path = Path(argv[1]).resolve()
            assert self.allows(path)
            reads.append(path.name)
            content = path.read_text()
            return {'packet_id': f'packet-{len(reads)}', 'status': 'completed', 'exit_code': 0,
                'stdout': content, 'truncated': False,
                'source_reads': [{'path': str(path), 'content_sha256': hashlib.sha256(content.encode()).hexdigest()}]}
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            if len(turns) <= 5:
                value = {'tool': 'command', 'arguments': {'argv': ['cat', str(tmp_path / files[len(turns) - 1])],
                                                        'cwd': str(tmp_path)}}
            else:
                value = {'answer': 'The read maps provide partial guidance.',
                    'findings': [{'text': 'Observed guidance 4.', 'evidence_packets': ['packet-5']}],
                    'unresolved_questions': ['Further implementation details were not read.'],
                    'skill_selection': {'format': 'pc-skill-selection/1', 'selections': [{
                        'skill': 'fixture', 'resource': 'needs.md',
                        'content_sha256': hashlib.sha256((tmp_path / 'needs.md').read_bytes()).hexdigest(),
                        'line_start': 1, 'line_end': 1, 'reason': 'Observed task guidance'}],
                        'synthesis': 'Observed guidance 4.', 'unresolved': ['Unread details.']}}
            return {'status': 'available', 'text': json.dumps(value)}
    command = Command([tmp_path], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=command, tools=lambda *a: pytest.fail('unexpected tool'), fence=lambda *a: True)
    result = worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'skill', 'question': 'Read skill maps for guidance',
        'skill': {'name': 'fixture', 'root': str(tmp_path)}, 'max_steps': 6, 'deadline_epoch': time.time() + 5})
    assert result['status'] == 'partial'
    assert len(turns) == 6
    assert reads == [*files, 'needs.md']  # Last read is authoritative final validation, not a model-requested call.
    assert result['findings'][0]['evidence_packets'] == ['packet-5']
    assert result['skill_selection']['selections'][0]['resource'] == 'needs.md'
    assert all('hidden' not in observation for observation in result['observations'])


@pytest.mark.parametrize('budget', [6, 2])
def test_initial_prompt_announces_actual_round_budget_and_reserved_final(tmp_path, budget):
    turns = []
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            return {'status': 'available', 'text': json.dumps({'answer': 'No further inquiry needed.', 'findings': []})}
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: pytest.fail('unexpected tool'), fence=lambda *a: True)
    result = worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate', 'question': 'Explain available evidence',
                        'max_steps': budget})
    assert result['status'] == 'completed'
    assert len(turns) == 1
    opening = turns[0]['messages'][0]['content']
    assert f'You have {budget} model rounds total for this attempt.' in opening
    assert 'Reserve the final round for final JSON synthesis of the evidence gathered so far' in opening
    assert 'no further command or tool calls are permitted on that final round' in opening


def test_argument_schemas_are_available_on_first_model_turn(tmp_path):
    turns = []
    schemas = {'log': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'additionalProperties': False},
               'evidence': {'type': 'object', 'properties': {'subject': {'type': 'string'}}, 'required': ['subject']}}
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            return {'status': 'available', 'text': json.dumps({'answer': 'No additional tools needed.', 'findings': []})}
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=lambda *a: pytest.fail('unexpected tool'), fence=lambda *a: True)
    worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate', 'question': 'q', 'tool_argument_schemas': schemas})
    opening = turns[0]['messages'][0]['content']
    assert json.dumps(schemas, separators=(',', ':')) in opening
    assert 'Answer promptly once gathered evidence suffices' in opening
    assert 'Log is optional' in opening
    assert len(json.dumps(turns[0]).encode()) < 60000


def test_invalid_tool_argument_feedback_consumes_one_round_and_is_not_evidence(tmp_path):
    turns, calls = [], []
    retained = {'packet_id': 'source-1', 'source': 'Observed source fact'}
    class Backend:
        def run_observer_turn(self, request):
            turns.append(request)
            if len(turns) == 1:
                value = {'tool': 'log', 'arguments': {'offset': 0}}
            else:
                assert any('invalid_tool_arguments' in m['content'] for m in request['messages'])
                value = {'answer': 'The retained source supports the answer.',
                    'findings': [{'text': 'Observed source fact', 'evidence_packets': ['source-1']}]}
            return {'status': 'available', 'text': json.dumps(value)}
    def tools(name, arguments):
        calls.append((name, arguments))
        return {'packet_id': 'validation-1', 'status': 'denied', 'reason': 'invalid_tool_arguments',
            'accepted': False, 'dispatched': False, 'tool': name, 'validation_error': 'offset is unsupported',
            'validation_data': {'is_source_evidence': False},
            'corrective_action': 'Use the advertised argument schema and retained evidence.'}
    runner = ReadOnlyCommandRunner([tmp_path], packetize=lambda p: 'packet')
    worker = ObserverWorkerPort(Backend(), command=runner, tools=tools, fence=lambda *a: True)
    result = worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate', 'question': 'q', 'max_steps': 2,
        'observations': [retained], 'tool_argument_schemas': {'log': {'type': 'object', 'additionalProperties': False}}})
    assert result['status'] == 'completed'
    assert len(turns) == 2 and len(calls) == 1
    assert result['findings'][0]['evidence_packets'] == ['source-1']
    assert result['observations'][-1]['validation_data']['is_source_evidence'] is False


@pytest.mark.parametrize('schemas', [{'mutation': {}}, {'log': []}])
def test_schema_metadata_cannot_add_tools_or_invalid_contracts(tmp_path, schemas):
    worker = ObserverWorkerPort(None, command=ReadOnlyCommandRunner([tmp_path], packetize=lambda p: 'packet'),
                                tools=lambda *a: None, fence=lambda *a: True)
    with pytest.raises(ValueError, match='invalid tool argument schemas'):
        worker.run({'job_id': 'job', 'attempt': 1, 'mode': 'investigate', 'question': 'q', 'tool_argument_schemas': schemas})
