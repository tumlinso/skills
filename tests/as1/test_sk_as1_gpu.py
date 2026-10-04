"""GPU protocol acceptance and separately required installed-hardware evidence.

The isolated cases use real host coordination and harmless OS child processes,
but explicitly simulated GPU observations/model turns. They are not inference
or hardware qualification. This module never launches a GPU workload itself.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

SKILLS = Path(__file__).resolve().parents[2]
for directory in (SKILLS / 'todo-orchestrator', SKILLS / 'local-coding-worker'):
    sys.path.insert(0, str(directory))

from todo_orchestrator.background.host import HostCoordinator
from todo_orchestrator.background.store import _alive, _process_start
from local_worker.observer_runtime import ObserverWorkerPort, ReadOnlyCommandRunner

fixture_spec = importlib.util.spec_from_file_location(
    'as1_gpu_model_fixtures', SKILLS / 'local-coding-worker/tests/test_supervisor.py')
fixtures = importlib.util.module_from_spec(fixture_spec)
fixture_spec.loader.exec_module(fixtures)


class IsolatedHost(fixtures._Host):
    """Simulated topology; reservations/preemption use the real native ledger."""
    def __init__(self):
        super().__init__()
        self.supervisor_pid = None
        self.ledger = HostCoordinator()
        self.ledger.upsert_resources(self.list())

    def reserve_service(self, **kwargs):
        request = kwargs.pop('resource_request')
        if self.supervisor_pid is not None:
            kwargs['pid'] = self.supervisor_pid
        result = self.ledger.reserve_service(request=request, **kwargs)
        return None if result is None else {'owner_id': result[0], 'resource_ids': result[1]}

    def set_priority(self, owner_id, priority):
        return self.ledger.set_priority(owner_id, priority)

    def heartbeat(self, owner_id, pid=None):
        self.ledger.heartbeat(owner_id, pid)

    def preempt_requested(self, owner_id):
        return self.ledger.preempt_requested(owner_id)

    def release(self, owner_id):
        self.ledger.release(owner_id)

    def reconcile_current_service_owners(self, **kwargs):
        return self.ledger.reconcile_current_service_owners(**kwargs)


class ProcessModel(fixtures._Service):
    """Harmless CPU children stand in for owned models, never GPU inference."""
    def __init__(self):
        super().__init__()
        self.processes = {}
        self.gpus = {}
        self.retain_memory = False
        self.fail_evict = False
        self.blocked = False
        self.samples = []
        self.run_hook = None
        self.fail_describe = False

    def start(self, name, context):
        handle = super().start(name, context)
        self.processes[handle] = subprocess.Popen(
            [sys.executable, '-c', 'import time; time.sleep(120)'],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        self.gpus[handle] = context['service_profile']['allocated_gpu_uuids']
        return handle

    def describe(self, handle):
        if self.fail_describe:
            raise RuntimeError('explicit fixture descriptor failure after process startup')
        return {'base_url': 'http://127.0.0.1:1', 'pid': self.processes[handle].pid}

    def owned_process_descriptor(self, handle):
        return {'pid': self.processes[handle].pid,
                'process_start': _process_start(self.processes[handle].pid)}

    def evict(self, name, handle):
        if self.fail_evict:
            raise RuntimeError('explicit fixture termination failure')
        process = self.processes[handle]
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=5)
        return super().evict(name, handle)

    def observe(self, uuids):
        processes = [{'uuid': uuid, 'pid': process.pid}
                     for handle, process in self.processes.items() if process.poll() is None
                     for uuid in self.gpus[handle] if uuid in uuids]
        observation = {'available': True, 'processes': processes,
                       'devices': [{'uuid': uuid, 'memory_used_mib':
                           128 if self.retain_memory or any(p['uuid'] == uuid for p in processes) else 0}
                                   for uuid in uuids]}
        self.samples.append(observation)
        return observation

    def cleanup(self):
        self.fail_evict = False
        self.retain_memory = False
        for handle in self.processes:
            self.evict('llama', handle)

    def run(self, name, handle, request):
        self.requests.append(request)
        if self.run_hook:
            self.run_hook()
        return {'text': json.dumps(self.reply), 'usage': {'completion_tokens': 7}}


class GPUProtocolAcceptance(unittest.TestCase):
    def setUp(self):
        self.assertEqual(Path(sys.prefix).resolve(), Path('/home/tumlinson/project-control/.venv').resolve(),
                         'qualification must use the repaired assigned runtime interpreter')
        for module, expected in (
            ('local_worker.supervisor', SKILLS / 'local-coding-worker/local_worker/supervisor.py'),
            ('local_worker.observer_runtime', SKILLS / 'local-coding-worker/local_worker/observer_runtime.py'),
            ('todo_orchestrator.background.host', SKILLS / 'todo-orchestrator/todo_orchestrator/background/host.py')):
            self.assertEqual(Path(sys.modules[module].__file__).resolve(), expected,
                             'qualification imported a different source deployment')
        self.temporary = tempfile.TemporaryDirectory(prefix='as1-gpu-protocol-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        environment = patch.dict(os.environ, {'TODO_BACKGROUND_HOST_RUNTIME_DIR': str(self.root / 'host')})
        environment.start()
        self.addCleanup(environment.stop)
        self.host = IsolatedHost()
        self.service = ProcessModel()
        self.addCleanup(self.service.cleanup)
        self.backend = fixtures._PoolBackend(
            self.root, service_state_root=self.root / 'observer',
            profile=fixtures._profile(), cache=fixtures._Cache(),
            runtime=SimpleNamespace(host=self.host), adapter=self.service,
            service=self.service, topology_classifier=lambda: SimpleNamespace(mode='normal', status='available'),
            residency_observer=self.service.observe)
        self.addCleanup(self.backend.close)

    def foreground(self, uuids):
        owner, resources = self.host.ledger.begin_foreground(
            project_root=self.root, request={'ids': ['accelerator:' + u for u in uuids]},
            pid=os.getpid(), priority_class='clean_cuda_foreground')
        self.addCleanup(self.host.ledger.release, owner)
        return owner, resources

    @pytest.mark.as1_case('GPU-01')
    def test_idle_overlap_evicts_only_owned_slot_and_preserves_other_island(self):
        first, separate = self.backend.warm(), self.backend.warm()
        self.backend.release(first['service_lease_id'])
        self.backend.release(separate['service_lease_id'])
        owner, resources = self.foreground(first['gpu_uuids'])
        self.assertTrue(self.host.ledger.preempt_requested(first['owner_id']))
        self.assertFalse(self.host.ledger.preempt_requested(separate['owner_id']))
        self.assertFalse(self.host.ledger.activate_foreground(owner, resources))
        self.backend.poll()
        self.assertEqual([s['slot_id'] for s in self.backend.status()['slots']], [separate['slot_id']])
        self.assertEqual(self.host.ledger.owner(first['owner_id'])['state'], 'released')
        self.assertEqual(self.host.ledger.owner(separate['owner_id'])['state'], 'active')
        self.assertTrue(self.host.ledger.activate_foreground(owner, resources))
        reused = self.backend.warm()
        self.assertTrue(reused['reused'])
        self.assertEqual(reused['server_pid'], separate['server_pid'])
        self.backend.release(reused['service_lease_id'])

    @pytest.mark.as1_case('GPU-02')
    def test_adapter_failure_and_residual_vram_keep_physical_lease_until_observed_release(self):
        endpoint = self.backend.warm()
        self.backend.release(endpoint['service_lease_id'])
        owner, resources = self.foreground(endpoint['gpu_uuids'])
        self.service.fail_evict = True
        self.backend.poll()
        self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['state'], 'active')
        self.assertFalse(self.host.ledger.activate_foreground(owner, resources))
        self.assertTrue(any(p.poll() is None for p in self.service.processes.values()))
        self.service.fail_evict = False
        self.service.retain_memory = True
        self.backend.poll()
        self.assertFalse(self.host.ledger.activate_foreground(owner, resources))
        self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['state'], 'active')
        self.assertTrue(all(p.poll() is not None for p in self.service.processes.values()))
        self.assertTrue(self.service.samples[-1]['devices'])
        self.service.retain_memory = False
        self.backend.poll()
        self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['state'], 'released')
        self.assertTrue(self.host.ledger.activate_foreground(owner, resources))
        self.assertFalse(self.service.samples[-1]['processes'])
        self.assertTrue(all(d['memory_used_mib'] == 0 for d in self.service.samples[-1]['devices']))

    @pytest.mark.as1_case('GPU-02')
    def test_expired_supervisor_owner_cannot_hide_live_owned_model_process(self):
        # Reservation initially belongs to a real supervisor child. Production
        # startup must bind its model PID before that supervisor can disappear.
        dead_supervisor = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
        self.addCleanup(lambda: dead_supervisor.poll() is None and dead_supervisor.kill())
        dead_start = _process_start(dead_supervisor.pid)
        self.assertTrue(dead_start)
        self.host.supervisor_pid = dead_supervisor.pid
        endpoint = self.backend.warm()
        self.backend.release(endpoint['service_lease_id'])
        self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['pid'], endpoint['server_pid'])
        dead_supervisor.terminate()
        dead_supervisor.wait(timeout=5)
        self.assertGreater(dead_supervisor.pid, 0)
        self.assertFalse(_alive(dead_supervisor.pid, dead_start))
        with self.host.ledger.connect() as connection:
            connection.execute('UPDATE host_owners SET heartbeat_at=0 WHERE id=?', (endpoint['owner_id'],))
        self.host.ledger.sweep_stale(stale_seconds=0)
        self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['state'], 'active')
        owner, resources = self.foreground(endpoint['gpu_uuids'])
        self.assertFalse(self.host.ledger.activate_foreground(owner, resources))

    @pytest.mark.as1_case('GPU-02')
    def test_partial_startup_failure_keeps_failed_cleanup_owned_process_reserved(self):
        self.service.fail_describe = True
        self.service.fail_evict = True
        with self.assertRaises(RuntimeError):
            self.backend.warm()
        self.assertEqual(len(self.service.processes), 1)
        handle, process = next(iter(self.service.processes.items()))
        self.assertIsNone(process.poll())
        owner, resources = self.foreground(self.service.gpus[handle])
        self.assertFalse(self.host.ledger.activate_foreground(owner, resources),
                         'partial startup released a physical lease while owned child remained alive')
        self.service.fail_describe = False
        self.service.fail_evict = False
        self.backend.poll()
        self.assertIsNotNone(process.poll())
        self.assertTrue(self.host.ledger.activate_foreground(owner, resources))

    @pytest.mark.as1_case('GPU-03')
    def test_cooperative_turn_yield_restart_retains_durable_port_evidence_and_fences_late_answer(self):
        # The persistent callback/fence is a trusted broker PORT fixture. Real
        # Project Control job transactions are qualified by PC-JOBS/paired SQA.
        state_path = self.root / 'durable-job.json'
        state_path.write_text(json.dumps({'attempt': 1, 'observations': []}))
        endpoint, separate = self.backend.warm(), self.backend.warm()
        self.backend.release(separate['service_lease_id'])
        unrelated, unrelated_resources = self.foreground(['unrelated-protocol-device'])
        self.assertTrue(self.host.ledger.activate_foreground(unrelated, unrelated_resources))
        unrelated_before = self.host.ledger.owner(unrelated)
        selected_foreground = []

        def fence(job, attempt):
            return job == 'persistent-protocol-job' and json.loads(state_path.read_text())['attempt'] == attempt

        def checkpoint(job, attempt, observations):
            self.assertTrue(fence(job, attempt))
            staging = state_path.with_suffix('.pending')
            staging.write_text(json.dumps({'attempt': attempt, 'observations': observations}))
            staging.replace(state_path)

        def foreground_during_owned_turn():
            selected_foreground.append(self.foreground(endpoint['gpu_uuids']))
            self.backend.poll()
            self.assertTrue(any(p.pid == endpoint['server_pid'] and p.poll() is None
                                for p in self.service.processes.values()))
            self.assertEqual(self.host.ledger.owner(endpoint['owner_id'])['state'], 'active')
            self.assertFalse(self.host.ledger.activate_foreground(*selected_foreground[0]))
            self.assertEqual(self.host.ledger.owner(separate['owner_id'])['state'], 'active')
            self.service.run_hook = None

        self.service.run_hook = foreground_during_owned_turn
        self.service.reply = {'tool': 'search', 'arguments': {'query': 'durable finding'}}
        runner = ReadOnlyCommandRunner([self.root], packetize=lambda result: 'unused-command-packet')
        worker = ObserverWorkerPort(self.backend, command=runner,
            tools=lambda name, args: {'packet_id': 'durable-finding-packet', 'source': 'exact protocol fact'},
            fence=fence, checkpoint=checkpoint)
        request = {'job_id': 'persistent-protocol-job', 'attempt': 1, 'mode': 'investigate',
                   'question': 'retain a finding through eviction', 'scope': str(self.root),
                   'session_id': endpoint['service_lease_id'], 'max_steps': 3}
        yielded = worker.run(request)
        self.assertEqual(yielded['status'], 'yielding', yielded)
        self.assertEqual(yielded['reason'], 'foreground_preemption')
        retained = json.loads(state_path.read_text())
        self.assertEqual(len(retained['observations']), 1)
        self.assertEqual(retained['observations'][0]['packet_id'], 'durable-finding-packet')
        self.backend.release(endpoint['service_lease_id'])
        self.assertTrue(self.host.ledger.activate_foreground(*selected_foreground[0]))
        self.assertEqual(self.host.ledger.owner(unrelated), unrelated_before)
        self.assertEqual(self.host.ledger.owner(separate['owner_id'])['state'], 'active')
        self.host.ledger.release(selected_foreground[0][0])

        # Reconstruct worker and durable state; resume a NEW attempt, preserving
        # only exact prior observations. No old in-memory worker state is reused.
        retained['attempt'] = 2
        state_path.write_text(json.dumps(retained))
        reloaded = self.backend.warm()
        self.service.reply = {'answer': 'continued from durable evidence', 'findings': [], 'unresolved_questions': []}
        restarted = ObserverWorkerPort(self.backend, command=runner, tools=lambda *args: self.fail('unexpected tool'),
                                       fence=fence, checkpoint=checkpoint)
        resumed = restarted.run({**request, 'attempt': 2, 'session_id': reloaded['service_lease_id'],
                                 'observations': json.loads(state_path.read_text())['observations']})
        self.assertEqual(resumed['status'], 'completed', resumed)
        self.assertEqual(resumed['observations'], yielded['observations'])
        self.assertIn('durable-finding-packet', json.dumps(self.service.requests[-1]))
        durable_before_late = state_path.read_bytes()
        stale = worker.run(request)
        self.assertEqual(stale['status'], 'stale_attempt', stale)
        self.assertEqual(state_path.read_bytes(), durable_before_late)
        def supersede_during_turn():
            state = json.loads(state_path.read_text())
            state['attempt'] = 3
            state_path.write_text(json.dumps(state))
            self.service.run_hook = None
        self.service.run_hook = supersede_during_turn
        late = restarted.run({**request, 'attempt': 2, 'session_id': reloaded['service_lease_id'],
                              'observations': retained['observations']})
        self.assertEqual(late['status'], 'stale_attempt', late)
        self.assertNotIn('answer', late)
        self.assertEqual(json.loads(state_path.read_text()), {**retained, 'attempt': 3})
        self.backend.release(reloaded['service_lease_id'])


class InstalledGPUAcceptance(unittest.TestCase):
    @pytest.mark.as1_case('GPU-04')
    def test_root_approved_installed_multigpu_probe_is_required(self):
        pointer = os.environ.get('SK_AS1_GPU_QUALIFICATION', str(
            SKILLS / 'planning/adaptive-surface-v1/validation/skills-gpu-hardware-qualification.json'))
        receipt_path = Path(pointer).resolve()
        self.assertTrue(receipt_path.is_file(), 'GPU-04 requires root-approved actual installed multi-GPU '
                        'qualification at ' + str(receipt_path) + '; protocol fixtures are insufficient')
        receipt = json.loads(receipt_path.read_text())
        self.assertEqual(receipt['format'], 'sk-as1-gpu-hardware/1')
        self.assertEqual(receipt['source_identity']['skills_root'], str(SKILLS))
        for relative in ('local-coding-worker/local_worker/supervisor.py',
                         'todo-orchestrator/todo_orchestrator/background/host.py',
                         'cuda/scripts/cuda_controller.py', 'local-coding-worker/local_worker/residency.py'):
            self.assertEqual(receipt['source_identity']['sha256'][relative],
                             hashlib.sha256((SKILLS / relative).read_bytes()).hexdigest(),
                             'hardware proof does not qualify current source: ' + relative)
        # The receipt is an execution attestation, not cryptographic proof of
        # hardware. Require raw observed artifacts and independently check their
        # contents as well as their hashes. Never accept summary booleans alone.
        raw = {}
        for artifact in receipt['artifacts']:
            path = (receipt_path.parent / artifact['path']).resolve()
            self.assertTrue(path.is_relative_to(receipt_path.parent), 'artifact escaped qualification root')
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact['sha256'])
            self.assertNotIn(artifact['kind'], raw, 'duplicate proof kind')
            raw[artifact['kind']] = json.loads(path.read_text())
        self.assertTrue({'approval', 'discovery', 'controller', 'quiescence', 'reuse', 'cleanup'} <= raw.keys())
        approved = set(raw['approval']['resource_ids'])
        self.assertGreaterEqual(len(approved), 2, 'multi-GPU approval required')
        self.assertTrue(all(r.startswith('accelerator:GPU-') for r in approved))
        approved_uuids = {r.removeprefix('accelerator:') for r in approved}
        discovery = raw['discovery']
        self.assertEqual(set(discovery['approved_gpu_uuids']), approved_uuids)
        self.assertTrue(approved_uuids <= {d['uuid'] for d in discovery['devices']})
        self.assertTrue(discovery['topology'], 'dynamically observed topology missing')
        controller = raw['controller']
        self.assertTrue(controller['result']['ok'], controller['result'])
        self.assertEqual(controller['result']['status'], 'succeeded')
        self.assertEqual(controller['result']['returncode'], 0)
        self.assertTrue(controller['result']['evidence_id'])
        self.assertEqual(controller['lease']['format'], 'CUDA-FOREGROUND-LEASE/1')
        self.assertEqual(set(controller['lease']['resource_ids']), approved)
        self.assertEqual(set(controller['spec']['resources']['gpu_uuids']), approved_uuids)
        self.assertEqual(controller['spec']['resources']['gpus'], len(approved_uuids))
        proof = raw['quiescence']['controller']
        self.assertEqual(proof['format'], 'CUDA-QUIESCENCE/1')
        self.assertEqual(proof['state'], 'quiescent')
        self.assertEqual(set(proof['device_uuids']), approved_uuids)
        required = proof['required_consecutive_samples']
        self.assertGreaterEqual(required, 2)
        self.assertGreaterEqual(len(proof['observations']), required)
        for observation in proof['observations'][-required:]:
            self.assertTrue(observation['idle'])
            self.assertFalse(observation['busy'])
            self.assertFalse(observation['foreign_processes'])
            self.assertTrue(observation['samples'], 'raw observed device samples missing')
            for sample in observation['samples']:
                self.assertEqual({d['uuid'] for d in sample['devices']}, approved_uuids)
                self.assertFalse(sample['foreign_processes'])
        reuse = raw['reuse']
        self.assertTrue(reuse['reused'])
        self.assertEqual(set(reuse['before']['gpu_uuids']), approved_uuids)
        self.assertEqual(set(reuse['after']['gpu_uuids']), approved_uuids)
        for identity in ('server_pid', 'model_sha256', 'compatibility_key', 'slot_id'):
            self.assertEqual(reuse['before'][identity], reuse['after'][identity])
        for turn in ('first_turn', 'reload_turn', 'reuse_turn'):
            self.assertEqual(reuse[turn]['status'], 'available')
            self.assertTrue(reuse[turn]['text'].strip(), 'actual installed model turn missing')
            self.assertEqual(reuse[turn]['provider'], 'llama-server')
        eviction = raw['quiescence']['eviction']
        self.assertTrue(eviction['process_released'])
        self.assertTrue(eviction['memory_released'])
        self.assertEqual(set(eviction['gpu_uuids']), approved_uuids)
        self.assertTrue(eviction['observation']['available'])
        self.assertFalse(eviction['observation']['processes'])
        self.assertEqual({d['uuid'] for d in eviction['observation']['devices']}, approved_uuids)
        for device in eviction['observation']['devices']:
            self.assertLessEqual(device['memory_used_mib'], eviction['memory_baseline'][device['uuid']] + 16)
        cleanup = raw['cleanup']
        self.assertEqual(cleanup['remaining_slots'], [])
        self.assertEqual(cleanup['remaining_owned_leases'], [])
        self.assertEqual(cleanup['owned_model_pids'], [])
        self.assertTrue(cleanup['observation']['available'])
        self.assertFalse(cleanup['observation']['processes'])
        self.assertEqual({d['uuid'] for d in cleanup['observation']['devices']}, approved_uuids)
        self.assertEqual(cleanup['unrelated_before'], cleanup['unrelated_after'])
        self.assertTrue(cleanup['unrelated_before'], 'unrelated installed work preservation was not observed')


if __name__ == '__main__':
    unittest.main()
