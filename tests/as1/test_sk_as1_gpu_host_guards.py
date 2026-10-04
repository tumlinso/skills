"""Native same-database protection against the exact pre-AS1 frozen writer."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from contextlib import closing
from unittest.mock import patch

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / 'todo-orchestrator'))
from todo_orchestrator.background.host import HostCoordinator

OLD_SOURCE_REF = '6d24f551f2df4239fd5d5b5fa333d67b14135f3c'
OLD_SOURCE_SHA256 = '572da6bb48bf78b5faa52274b4d8d5d1cf3614766416d637e10f9388afc8933b'


class NativeHostGuardTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='gpu-native-host-guard-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        environment = patch.dict(os.environ, {'TODO_BACKGROUND_HOST_RUNTIME_DIR': str(self.root / 'host')})
        environment.start()
        self.addCleanup(environment.stop)
        self.host = HostCoordinator()
        self.host.upsert_resources([{'id': 'accelerator:GPU-guard', 'kind': 'accelerator'}])
        self.owner, self.resources = self.host.reserve_service(project_root=self.root,
            service_id='core4-local-guard', request={'ids': ['accelerator:GPU-guard']}, pid=os.getpid())
        self.grant = self.host.protect_residency(self.owner, memory_baseline={'GPU-guard': 0})
        self.child = None
        self.addCleanup(self.cleanup_owned)

    def proof(self, *, memory=0):
        metadata = json.loads(self.host.owner(self.owner)['residency_metadata_json'])
        return {'format': 'CORE4-RESIDENCY-QUIESCENCE/1', 'owner_id': self.owner,
                'owned_pid': metadata['model_pid'], 'observed_unix': time.time(),
                'observation': {'available': True, 'processes': [],
                                'devices': [{'uuid': 'GPU-guard', 'memory_used_mib': memory}]}}

    def release(self, proof=None, **kwargs):
        self.host.release(self.owner, residency_quiescence=self.proof() if proof is None else proof,
            residency_capability=kwargs.get('residency_capability', self.grant['residency_capability']),
            generation=kwargs.get('generation', self.grant['generation']))

    def cleanup_owned(self):
        if self.child is not None and self.child.poll() is None:
            self.child.terminate()
            self.child.wait(timeout=5)
        if self.host.owner(self.owner)['state'] == 'active':
            self.release()

    def spawned(self):
        self.child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(90)'], start_new_session=True)
        self.host.record_residency_process(self.owner, pid=self.child.pid,
            residency_capability=self.grant['residency_capability'], generation=self.grant['generation'])

    def old_writer(self):
        source = subprocess.check_output(['git', '-C', str(SKILLS), 'show',
            OLD_SOURCE_REF + ':todo-orchestrator/todo_orchestrator/background/host.py'])
        self.assertEqual(hashlib.sha256(source).hexdigest(), OLD_SOURCE_SHA256)
        path = self.root / 'frozen_host.py'
        path.write_bytes(source)
        name = 'todo_orchestrator.background._gpu_guard_frozen_host'
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module.HostCoordinator()

    def assert_owned(self):
        owner = self.host.owner(self.owner)
        self.assertEqual(owner['state'], 'active')
        self.assertEqual(owner['residency_protected'], 1)
        self.assertEqual(owner['resources'], self.resources)

    def test_exact_old_writer_dead_sweep_release_and_reconcile_keep_same_database_lease(self):
        old = self.old_writer()
        old.reconcile_current_service_owners(project_root=self.root, pid=os.getpid(), live_owner_ids=set())
        self.assert_owned()
        self.spawned()
        self.child.terminate()
        self.child.wait(timeout=5)
        with closing(self.host.connect()) as connection:
            connection.execute('UPDATE host_owners SET heartbeat_at=0 WHERE id=?', (self.owner,))
        self.assertEqual(old.sweep_stale(stale_seconds=0), 0)
        old.heartbeat(self.owner, pid=os.getpid())
        self.assertEqual(self.host.owner(self.owner)['pid'], self.child.pid)
        old.release(self.owner)
        self.assert_owned()
        self.release()
        self.assertEqual(self.host.owner(self.owner)['state'], 'released')
        self.assertEqual(self.host.owner(self.owner)['resources'], [])

    def test_guard_blocks_destructive_old_updates_deletes_replace_and_upsert(self):
        old = self.old_writer()
        with closing(old.connect()) as connection:
            connection.execute("UPDATE host_owners SET state='released' WHERE id=?", (self.owner,))
            connection.execute('DELETE FROM host_owners WHERE id=?', (self.owner,))
            connection.execute("UPDATE host_owners SET residency_protected=0 WHERE id=?", (self.owner,))
            connection.execute("UPDATE host_owners SET residency_metadata_json=json_set(residency_metadata_json,'$.generation','foreign') WHERE id=?", (self.owner,))
            connection.execute("UPDATE host_reservations SET state='released' WHERE owner_id=?", (self.owner,))
            connection.execute('DELETE FROM host_reservations WHERE owner_id=?', (self.owner,))
            columns = [row[1] for row in connection.execute('PRAGMA table_info(host_owners)')]
            row = connection.execute('SELECT * FROM host_owners WHERE id=?', (self.owner,)).fetchone()
            values = [row[column] for column in columns]
            values[columns.index('state')] = 'released'
            placeholders = ','.join('?' for _ in columns)
            connection.execute(f"INSERT OR REPLACE INTO host_owners({','.join(columns)}) VALUES({placeholders})", values)
            connection.execute(f"INSERT INTO host_owners({','.join(columns)}) VALUES({placeholders}) ON CONFLICT(id) DO UPDATE SET state='released'", values)
            connection.execute("INSERT OR REPLACE INTO host_reservations(resource_id,owner_id,state,acquired_at,heartbeat_at) VALUES(?,?,'active',?,?)",
                               ('accelerator:GPU-guard', 'foreign', time.time(), time.time()))
        self.assert_owned()

    def test_missing_wrong_generation_capability_and_untrusted_proof_cannot_release(self):
        for kwargs in ({}, {'residency_capability': '0' * 64}, {'generation': 'foreign'}):
            with self.assertRaises(ValueError):
                self.host.release(self.owner, residency_quiescence=self.proof(), **kwargs)
            self.assert_owned()
        for proof in ({'quiescent': True}, self.proof(memory=128),
                      {**self.proof(), 'observed_unix': time.time() - 60}):
            with self.assertRaises(ValueError):
                self.release(proof)
            self.assert_owned()

    def test_same_capability_in_other_process_cannot_release_live_origin_reservation(self):
        script = '''import json,sys
from todo_orchestrator.background.host import HostCoordinator
request=json.load(sys.stdin)
try:
 HostCoordinator().release(**request)
except ValueError:
 sys.exit(0)
sys.exit(1)
'''
        request = {'owner_id': self.owner, 'residency_quiescence': self.proof(),
                   'residency_capability': self.grant['residency_capability'], 'generation': self.grant['generation']}
        result = subprocess.run([sys.executable, '-c', script], input=json.dumps(request), capture_output=True,
            text=True, env={**os.environ, 'PYTHONPATH': str(SKILLS / 'todo-orchestrator')})
        self.assertEqual(result.returncode, 0, 'another process acquired cleanup authority')
        self.assert_owned()

    def test_spawned_live_child_or_unreleased_vram_stays_protected(self):
        self.spawned()
        with self.assertRaises(ValueError):
            self.release()
        self.child.terminate()
        self.child.wait(timeout=5)
        with self.assertRaises(ValueError):
            self.release(self.proof(memory=128))
        self.host.sweep_stale(stale_seconds=0)
        self.assert_owned()
        self.release()

    def test_observation_delay_cannot_refresh_old_physical_snapshot(self):
        # No wall-clock sleep: the trusted callback represents a slow query.
        sys.path.insert(0, str(SKILLS / 'local-coding-worker'))
        from local_worker.supervisor import ProductionBackend
        sample = self.proof()['observation']
        backend = object.__new__(ProductionBackend)
        backend._observe_residency = lambda uuids: sample
        with patch('local_worker.supervisor.time.time', return_value=time.time() - 10):
            observation = backend._residency_sample(['GPU-guard'])
        delayed_proof = {**self.proof(), 'observation': observation,
                         'observed_unix': observation['observed_unix']}
        with self.assertRaisesRegex(ValueError, 'observation_stale'):
            self.release(delayed_proof)
        self.assert_owned()


if __name__ == '__main__':
    unittest.main()
