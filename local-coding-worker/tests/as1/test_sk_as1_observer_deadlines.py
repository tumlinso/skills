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
