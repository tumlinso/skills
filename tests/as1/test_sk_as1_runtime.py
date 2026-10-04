"""RUN-01..03 behavioral acceptance; scripted turns are not inference proof.

The command cases execute real Bubblewrap, never substitute a subprocess mock.
All authority fixtures are disposable; no live Todo or model/GPU is started.
"""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import pytest

SKILLS = Path(__file__).resolve().parents[2]
for directory in (SKILLS / 'todo-orchestrator', SKILLS / 'todo-orchestrator/tests',
                  SKILLS / 'local-coding-worker', SKILLS / 'integrations/coding-workflow-mcp'):
    sys.path.insert(0, str(directory))

from local_worker.observer_runtime import ObserverWorkerPort, ReadOnlyCommandRunner


class ScriptedBackend:
    """Deterministic protocol fixture: it does not load or verify a model."""
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.preempt_requested = False
        self.hook = None

    def run_observer_turn(self, request):
        self.requests.append(copy.deepcopy(request))
        if self.hook:
            self.hook()
        reply = self.replies.pop(0)
        return {'status': 'available', 'text': json.dumps(reply),
                'model_id': 'scripted-protocol-fixture', 'warm_model_reused': True}

    def preemption_status(self, session_id):
        return {'preempt_requested': self.preempt_requested, 'draining': False}


def final(answer='bounded fixture answer', **extra):
    return {'answer': answer, 'findings': [], 'unresolved_questions': [], **extra}


class AS1RuntimeAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / 'trusted'
        self.root.mkdir()
        self.source = self.root / 'source.txt'
        self.source.write_text('trusted source\n')
        self.packets = []
        self.generation = 1
        self.checkpoints = []
        self.tool_calls = []
        self.runner = ReadOnlyCommandRunner([self.root], packetize=self.packetize)

    def packetize(self, payload):
        self.packets.append(copy.deepcopy(payload))
        return 'fixture-packet-' + str(len(self.packets))

    def worker(self, backend):
        def tool(name, arguments):
            self.tool_calls.append((name, arguments))
            return {'status': 'ok', 'packet_id': 'fixture-semantic-packet'}
        return ObserverWorkerPort(backend, command=self.runner, tools=tool,
                                  fence=lambda job, attempt: attempt == self.generation,
                                  checkpoint=lambda job, attempt, observations:
                                  self.checkpoints.append((job, attempt, copy.deepcopy(observations))))

    def request(self, **changes):
        return {'job_id': 'fixture-job', 'attempt': 1, 'mode': 'investigate',
                'question': 'Read the relevant source', 'scope': str(self.root),
                'max_steps': 4, **changes}

    def command(self, argv, **changes):
        return self.runner.run(argv, cwd=str(self.root), **changes)

    def selection(self, resource='SKILL.md'):
        return {'format': 'pc-skill-selection/1', 'synthesis': 'fixture selection',
                'selections': [{'skill': 'tiny', 'resource': resource,
                                'reason': 'read native prerequisite',
                                'content_sha256': hashlib.sha256((self.root / resource).read_bytes()).hexdigest(),
                                'line_start': 1, 'line_end': 1}]}

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_modes_share_transport_but_never_share_job_context(self):
        (self.root / 'SKILL.md').write_text('fixture entry\n')
        backend = ScriptedBackend([final('investigation'),
            {'tool': 'command', 'arguments': {'argv': ['cat', str(self.root / 'SKILL.md')],
                                             'cwd': str(self.root)}},
            final('skill synthesis', skill_selection=self.selection())])
        worker = self.worker(backend)
        first = worker.run(self.request(question='caller-one-private-hint', session_id='warm-session'))
        second = worker.run(self.request(job_id='skill-job', mode='skill', question='caller-two',
                                         skill={'name': 'tiny', 'root': str(self.root)},
                                         session_id='warm-session'))
        self.assertEqual(first['status'], 'completed')
        self.assertEqual(second['status'], 'completed')
        self.assertEqual(len(backend.requests), 3)
        one, two = backend.requests[:2]
        self.assertEqual(one['format'], 'PC-LOCAL-INVESTIGATOR-TURN/2')
        self.assertEqual(one['session_id'], two['session_id'])
        self.assertIn('caller-one-private-hint', json.dumps(one['messages']))
        self.assertNotIn('caller-one-private-hint', json.dumps(two['messages']))
        self.assertNotEqual(one['messages'][0], two['messages'][0])
        self.assertEqual(self.tool_calls, [])
        self.assertEqual(list(self.root.glob('*.sqlite*')), [])

    @pytest.mark.as1_case('RUN-01')
    def test_skill_follows_native_files_agentically_without_eager_injection(self):
        (self.root / 'SKILL.md').write_text('entry-secret-route: read refs/route.md\n')
        (self.root / 'refs').mkdir()
        (self.root / 'refs/route.md').write_text('nested-prerequisite: prerequisite.md\n')
        (self.root / 'refs/prerequisite.md').write_text('selected-native-prerequisite\n')
        turns = [{'tool': 'command', 'arguments': {'argv': ['/usr/bin/cat', str(path)],
                                                  'cwd': str(self.root)}}
                 for path in (self.root / 'SKILL.md', self.root / 'refs/route.md',
                              self.root / 'refs/prerequisite.md')]
        backend = ScriptedBackend(turns + [final('selection after native reads',
                                skill_selection=self.selection('refs/prerequisite.md'))])
        result = self.worker(backend).run(self.request(mode='skill',
                                        skill={'name': 'tiny', 'root': str(self.root)}, max_steps=6))
        self.assertEqual(result['status'], 'completed')
        self.assertNotIn('entry-secret-route', json.dumps(backend.requests[0]['messages']))
        self.assertNotIn('nested-prerequisite', json.dumps(backend.requests[0]['messages']))
        self.assertIn('entry-secret-route', json.dumps(backend.requests[1]['messages']))
        self.assertIn('nested-prerequisite', json.dumps(backend.requests[2]['messages']))
        self.assertIn('selected-native-prerequisite', json.dumps(backend.requests[3]['messages']))
        self.assertGreaterEqual(len(self.packets), 3)
        self.assertTrue(self.checkpoints)

    @pytest.mark.as1_case('RUN-01')
    def test_skill_final_cannot_replace_agent_entry_and_router_reads(self):
        (self.root / 'SKILL.md').write_text('Native entry: read refs/router.md\n')
        (self.root / 'refs').mkdir()
        (self.root / 'refs/router.md').write_text('Read prerequisite.md before selecting\n')
        backend = ScriptedBackend([final('fabricated selection', skill_selection=self.selection())])
        result = self.worker(backend).run(self.request(mode='skill',
                            skill={'name': 'tiny', 'root': str(self.root)}))
        self.assertIn(result['status'], ('partial', 'failed'))
        self.assertNotIn('skill_selection', result)

    @pytest.mark.as1_case('RUN-01')
    def test_skill_cannot_select_unread_nested_route_via_final_validation(self):
        (self.root / 'SKILL.md').write_text('Native entry: read refs/router.md\n')
        (self.root / 'refs').mkdir()
        (self.root / 'refs/router.md').write_text('Read prerequisite.md before selecting\n')
        (self.root / 'refs/prerequisite.md').write_text('native prerequisite\n')
        backend = ScriptedBackend([
            {'tool': 'command', 'arguments': {'argv': ['cat', str(self.root / 'SKILL.md')],
                                             'cwd': str(self.root)}},
            final('unread nested selection', skill_selection=self.selection('refs/prerequisite.md'))])
        result = self.worker(backend).run(self.request(mode='skill',
                            skill={'name': 'tiny', 'root': str(self.root)}))
        self.assertIn(result['status'], ('partial', 'failed'))
        self.assertNotIn('skill_selection', result)

    @pytest.mark.as1_case('RUN-01')
    def test_forbidden_tools_cannot_reach_injected_authority(self):
        for name in ('delegate_task', 'collect_delegation', 'coordinate_task', 'next_task',
                     'finish_task', 'amend_project', 'investigate', 'skill', 'read'):
            with self.subTest(tool=name):
                backend = ScriptedBackend([{'tool': name, 'arguments': {}}, final()])
                result = self.worker(backend).run(self.request(max_steps=2))
                self.assertIn(result['status'], ('completed', 'partial', 'failed'))
                self.assertEqual(self.tool_calls, [])
                self.assertIn('denied', json.dumps(result).lower())

    @pytest.mark.as1_case('RUN-02')
    def test_stale_attempt_cannot_commit_model_answer_or_command_observation(self):
        backend = ScriptedBackend([final('late answer must not be published')])
        backend.hook = lambda: setattr(self, 'generation', 2)
        result = self.worker(backend).run(self.request())
        self.assertEqual(result['status'], 'stale_attempt')
        self.assertNotIn('late answer must not be published', json.dumps(result))
        self.assertEqual(self.packets, [])
        self.assertEqual(self.checkpoints, [])
        backend = ScriptedBackend([{'tool': 'command', 'arguments': {
            'argv': ['/usr/bin/cat', str(self.source)], 'cwd': str(self.root)}}])
        result = self.worker(backend).run(self.request())
        self.assertEqual(result['status'], 'stale_attempt')
        self.assertEqual(backend.requests, [])
        self.assertEqual(self.packets, [])

    @pytest.mark.as1_case('RUN-02')
    def test_attempt_superseded_during_real_command_cannot_packetize_or_checkpoint(self):
        backend = ScriptedBackend([{'tool': 'command', 'arguments': {
            'argv': ['/usr/bin/cat', str(self.source)], 'cwd': str(self.root)}}])
        worker = self.worker(backend)
        real_popen = subprocess.Popen
        def launch_and_supersede(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            self.generation = 2
            return process
        with patch('local_worker.observer_runtime.subprocess.Popen', side_effect=launch_and_supersede):
            result = worker.run(self.request())
        self.assertEqual(result['status'], 'stale_attempt')
        self.assertEqual(len(backend.requests), 1)
        self.assertEqual(self.packets, [])
        self.assertEqual(self.checkpoints, [])

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_bounded_model_output_and_unobserved_citations_are_partial(self):
        for reply in (final('x' * 17000), final(findings=[{
            'text': 'unsupported ownership claim', 'evidence_packets': ['unobserved-packet']}])):
            with self.subTest(reply_size=len(json.dumps(reply))):
                result = self.worker(ScriptedBackend([reply])).run(self.request())
                self.assertEqual(result['status'], 'partial')
                self.assertTrue(result['unresolved_questions'])
                self.assertNotIn('answer', result)
                self.assertEqual(self.packets, [])

    @pytest.mark.as1_case('RUN-02')
    def test_evicted_backend_returns_resume_state_without_dropping_observations(self):
        class EvictedBackend:
            def run_observer_turn(self, request):
                return {'status': 'unavailable', 'reason': 'observer_session_unavailable'}
        retained = [{'packet_id': 'retained-packet', 'stdout': 'prior observed source'}]
        result = self.worker(EvictedBackend()).run(self.request(observations=retained))
        self.assertEqual(result['status'], 'queued_after_eviction')
        self.assertEqual(result['observations'], retained)
        self.assertEqual(self.packets, [])
        self.assertEqual(self.checkpoints, [])

    @pytest.mark.as1_case('RUN-02')
    def test_cooperative_yield_preserves_work_and_resume_is_job_scoped(self):
        backend = ScriptedBackend([{'tool': 'command', 'arguments': {
            'argv': ['/usr/bin/cat', str(self.source)], 'cwd': str(self.root)}}, final('resumed')])
        worker = self.worker(backend)
        yielded = worker.run(self.request(max_steps=1))
        self.assertIn(yielded['status'], ('yielding', 'partial'))
        self.assertTrue(yielded['observations'])
        self.assertTrue(self.checkpoints)
        resumed = worker.run(self.request(observations=yielded['observations']))
        self.assertEqual(resumed['status'], 'completed')
        self.assertIn('trusted source', json.dumps(backend.requests[-1]['messages']))
        backend.preempt_requested = True
        before = len(backend.requests)
        preempted = worker.run(self.request(session_id='warm-session'))
        self.assertEqual(preempted['status'], 'yielding')
        self.assertEqual(len(backend.requests), before)

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_real_bwrap_argv_readonly_scratch_network_credentials_devices(self):
        literal = 'literal; $(touch forbidden)'
        read = self.command(['/usr/bin/printf', '%s', literal])
        self.assertEqual(read['status'], 'completed', read)
        self.assertEqual(read['stdout'], literal)
        self.assertFalse((self.root / 'forbidden').exists())
        denied = self.command(['/usr/bin/python3', '-c',
                               'from pathlib import Path; Path("source.txt").write_text("changed")'])
        self.assertNotEqual(denied['exit_code'], 0)
        self.assertEqual(self.source.read_text(), 'trusted source\n')
        script = ('import os,socket; from pathlib import Path; '
                  'assert not os.environ.get("AS1_FIXTURE_SECRET"); '
                  'assert not Path("/dev/nvidia0").exists(); '
                  'Path("/tmp/scratch").write_text("allowed"); '
                  's=socket.socket(); s.settimeout(.2); '
                  '\ntry: s.connect(("198.51.100.1", 443))\n'
                  'except OSError: print("network-denied")\n'
                  'else: raise AssertionError("network escaped")')
        with patch.dict(os.environ, {'AS1_FIXTURE_SECRET': 'never-expose-fixture-secret'}):
            safe = self.command(['/usr/bin/python3', '-c', script])
        self.assertEqual(safe['exit_code'], 0, safe)
        self.assertIn('network-denied', safe['stdout'])
        for result in (read, denied, safe):
            self.assertTrue(result['packet_id'])
            self.assertEqual(result['scope']['provenance'], 'coarse_volatile')
        outside = self.runner.run(
            ['/usr/bin/pwd'], cwd='/', timeout_seconds=1)
        self.assertEqual(outside['status'], 'denied')

    @pytest.mark.as1_case('RUN-02')
    def test_existing_production_supervisor_reuses_one_verified_slot(self):
        # Reuse established source fixtures around the actual ProductionBackend;
        # cache/adapter/resource fakes prove its protocol, never physical inference.
        fixture_path = SKILLS / 'local-coding-worker/tests/test_supervisor.py'
        spec = importlib.util.spec_from_file_location('as1_supervisor_fixtures', fixture_path)
        fixtures = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fixtures)
        backend, runtime, service = fixtures.ServicePoolTests().backend()
        self.addCleanup(backend.close)
        first = backend.warm(compute_profile='narrow')
        backend.release(first['service_lease_id'])
        second = backend.warm(compute_profile='narrow')
        self.assertTrue(second['reused'])
        for identity in ('slot_id', 'server_pid', 'model_sha256', 'compatibility_key'):
            self.assertEqual(first[identity], second[identity])
        self.assertEqual(service.starts, 1)
        backend.release(second['service_lease_id'])

    @pytest.mark.as1_case('RUN-02')
    def test_command_bounds_timeout_cleanup_and_packetization_failure(self):
        large = self.command(['/usr/bin/python3', '-c', 'print("x" * 1000000)'], max_output_bytes=1024)
        self.assertTrue(large['truncated'])
        self.assertLessEqual(len((large['stdout'] + large['stderr']).encode()), 1024)
        start = time.monotonic()
        marker = 'as1-child-' + self.root.parent.name
        child_script = 'import time; time.sleep(30) # ' + marker
        timed = self.command(['/usr/bin/python3', '-c',
            'import subprocess,time; subprocess.Popen(["/usr/bin/python3","-c",' +
            repr(child_script) + '], start_new_session=True); time.sleep(30)'],
            timeout_seconds=.3)
        self.assertTrue(timed['timed_out'])
        self.assertLess(time.monotonic() - start, 4)
        for cmdline in Path('/proc').glob('[0-9]*/cmdline'):
            try:
                raw = cmdline.read_bytes()
            except (OSError, PermissionError):
                continue
            self.assertNotIn(marker.encode(), raw, 'sandbox child survived timeout: ' + str(cmdline))
        broken = ReadOnlyCommandRunner([self.root], packetize=lambda payload: (_ for _ in ()).throw(
            RuntimeError('fixture storage unavailable')))
        result = broken.run(['/usr/bin/cat', str(self.source)], cwd=str(self.root))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['reason'], 'packetization_failed')
        self.assertNotIn('trusted source', json.dumps(result))

    @pytest.mark.as1_case('RUN-02')
    def test_invalid_utf8_cannot_expand_delivered_output_past_byte_budget(self):
        result = self.command(['/usr/bin/python3', '-c',
                              'import os; os.write(1, bytes([255])*16)'], max_output_bytes=16)
        self.assertLessEqual(len((result['stdout'] + result['stderr']).encode()), 16)
        self.assertTrue(result['truncated'])
        self.assertTrue(result['packet_id'])

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_invalid_utf8_source_proof_never_hashes_replacement_text_as_file_bytes(self):
        entry = self.root / 'SKILL.md'
        entry.write_bytes(b'\xff\n')
        result = self.command(['/usr/bin/cat', str(entry)], max_output_bytes=8192)
        self.assertEqual(result['exit_code'], 0, result)
        reads = result.get('source_reads', [])
        encoding_disclosure = json.dumps(result).lower().replace('-', '_')
        if reads:
            self.assertEqual(len(reads), 1)
            self.assertEqual(reads[0]['path'], str(entry))
            self.assertEqual(reads[0]['content_sha256'], hashlib.sha256(entry.read_bytes()).hexdigest())
            self.assertTrue('invalid_utf8' in encoding_disclosure or 'non_utf8' in encoding_disclosure)
        else:
            self.assertTrue('invalid_utf8' in encoding_disclosure or 'non_utf8' in encoding_disclosure)
            self.assertIn('exact source proof unavailable', encoding_disclosure)
            self.assertNotIn('content_sha256', json.dumps(result))
        self.assertTrue(result['packet_id'])

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_explicit_credentials_hidden_even_inside_trusted_read_mount(self):
        secret = self.root / 'credential.txt'
        secret.write_text('fixture-private-credential-body')
        runner = ReadOnlyCommandRunner([self.root], packetize=self.packetize, credential_paths=(secret,))
        result = runner.run(['/usr/bin/cat', str(secret)], cwd=str(self.root))
        self.assertNotIn('fixture-private-credential-body', json.dumps(result))
        self.assertNotIn('fixture-private-credential-body', json.dumps(self.packets))
        normal = runner.run(['/usr/bin/cat', str(self.source)], cwd=str(self.root))
        self.assertEqual(normal['stdout'], 'trusted source\n', normal)

    @pytest.mark.as1_case('RUN-01', 'RUN-02')
    def test_explicit_exclusion_also_masks_exposed_runtime_library_mounts(self):
        # Public harmless host file stands in for an explicitly excluded secret.
        # /usr is exposed for executables even though it is not a trusted root.
        target = Path('/usr/lib/os-release')
        self.assertTrue(target.is_file(), 'required real sandbox fixture missing')
        canonical = target.read_text()
        self.assertTrue(canonical)
        runner = ReadOnlyCommandRunner([self.root], packetize=self.packetize,
                                       credential_paths=(target,))
        result = runner.run(['/usr/bin/cat', str(target)], cwd=str(self.root))
        self.assertNotEqual(result['stdout'], canonical, 'explicit runtime-mounted exclusion leaked')
        self.assertEqual(result['stdout'], '')
        self.assertNotIn(canonical, json.dumps(self.packets))

    @pytest.mark.as1_case('RUN-03')
    def test_internal_coding_delegate_collect_remains_real_kernel_functionality(self):
        from v2_helpers import V2Repo, base_plan, safe_task
        from todo_orchestrator.workflow.capabilities import WorkflowCapabilityLocator
        from todo_orchestrator.workflow.protocol import WorkflowProtocol
        from todo_orchestrator.workflow.service import WorkflowKernel
        class CandidateFixture:
            def delegate(self, **kwargs):
                return {'status': 'running'}
            def collect(self, **kwargs):
                return {'status': 'candidate_available', 'kind': 'source_finding',
                        'result': {'summary': 'bounded fixture'}, 'artifacts': []}
        repo = V2Repo()
        self.addCleanup(repo.close)
        (repo.root / 'src/a').mkdir(parents=True)
        (repo.root / 'src/a/unit.py').write_text('value = 1\n')
        repo.apply(base_plan([safe_task('A', 'src/a')]))
        locator = WorkflowCapabilityLocator(Path(self.temporary.name) / 'capabilities')
        protocol = WorkflowProtocol(WorkflowKernel(locator=locator, local_worker_adapter=CandidateFixture()), locator)
        claimed = protocol.next_task(repo_root=str(repo.root))
        delegated = protocol.delegate_task(workflow_handle=claimed['workflow_handle'],
                    delegated_objective='Inspect one bounded file', mode='readonly')
        self.assertEqual(delegated['status'], 'claimed')
        collected = protocol.collect_delegation(delegation_handle=delegated['delegation_handle'])
        self.assertFalse(collected['parent_task_completed'])
        with repo.service.db.read() as conn:
            self.assertEqual(conn.execute("SELECT status FROM tasks WHERE id='A'").fetchone()[0], 'in_progress')

    @pytest.mark.as1_case('RUN-03')
    def test_native_model_routing_rejects_dormant_delegation_before_handler(self):
        from coding_workflow_mcp._canonical import canonical_server
        from coding_workflow_mcp.native_routing import NativeRoutingFastMCP
        from mcp.server.fastmcp.exceptions import ToolError
        # Actual supported Skills factory installs the guard; no synthetic
        # server class or patched discovery/dispatch stands in for integration.
        with patch.dict(os.environ, {'PROJECT_CONTROL_SKILLS_ROOT': str(SKILLS),
                                     'CODING_WORKFLOW_SKILLS_ROOT': str(SKILLS)}):
            server = canonical_server()
        self.assertIsInstance(server, NativeRoutingFastMCP)
        names = {tool.name for tool in asyncio.run(server.list_tools())}
        self.assertEqual(names, {'next_task', 'inspect_task', 'coordinate_task', 'finish_task'})
        for name in ('delegate_task', 'collect_delegation'):
            policy = server.routing_policy[name]
            self.assertEqual(policy['status'], 'temporarily_inactive')
            self.assertTrue(policy['preserve_implementation'])
            self.assertTrue(policy['reason'])
            self.assertIn('explicit operator decision', policy['reactivation'])
            self.assertIsNotNone(server._tool_manager.get_tool(name), 'internal handler was removed')
            # Canonical handlers demand arguments; explicit inactive denial
            # proves this never enters argument conversion or authority access.
            with self.assertRaises(ToolError) as denied:
                asyncio.run(server.call_tool(name, {}))
            self.assertIn('temporarily_inactive', str(denied.exception))
            self.assertIn('reactivation', str(denied.exception))


if __name__ == '__main__':
    unittest.main()
