from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from test_supervisor import _Adapter, _Cache, _Host, _PoolBackend, _Service, _profile
from local_worker.residency import process_identity
from local_worker.servers.llama_cpp import LlamaCppServerAdapter
from local_worker.supervisor import SupervisorError


class RecoveryHost(_Host):
    def __init__(self):
        super().__init__()
        self.metadata = {}

    def reserve_service(self, **kwargs):
        result = super().reserve_service(**kwargs)
        if result:
            self.metadata[result['owner_id']] = {'state': 'active', 'project_root': str(Path(kwargs['project_root']).resolve())}
            self.heartbeat(result['owner_id'], pid=kwargs['pid'])
        return result

    def heartbeat(self, owner_id, pid=None):
        if pid:
            self.metadata[owner_id].update(pid=pid, process_start=process_identity(pid)['process_start'])

    def owner(self, owner_id):
        return self.metadata[owner_id] | {'resources': list(self.owners.get(owner_id, []))}

    def release(self, owner_id):
        super().release(owner_id)
        self.metadata[owner_id]['state'] = 'released'


class ProcessService(_Service):
    def start(self, name, context):
        handle = super().start(name, context)
        self.process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(90)'], start_new_session=True)
        return handle

    def evict(self, name, handle):
        if self.process.poll() is None:
            self.process.terminate()
        self.process.wait(timeout=5)
        return super().evict(name, handle)


class ProcessAdapter(LlamaCppServerAdapter):
    def __init__(self, service):
        super().__init__(sys.executable)
        self.service = service

    def describe(self, handle):
        return {'base_url': 'http://127.0.0.1:1', 'pid': self.service.process.pid}

    owned_process_descriptor = describe


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.host = RecoveryHost()
        self.service = ProcessService()
        self.profile = _profile()
        self.profile['server']['binary'] = str(Path(sys.executable).resolve())
        self.first = self.backend()
        self.endpoint = self.first.warm()
        self.addCleanup(lambda: self.service.evict('llama', next(iter(self.service.handles))))

    def backend(self):
        return _PoolBackend(self.root, service_state_root=self.root / 'observer', profile=self.profile,
                            cache=_Cache(), runtime=SimpleNamespace(host=self.host), service=self.service,
                            adapter=ProcessAdapter(self.service),
                            topology_classifier=lambda: SimpleNamespace(mode='normal', status='available'))

    def marker(self):
        return self.first._marker_path(self.endpoint['slot_id'])

    def test_restart_recovers_only_marker_owned_child_and_lease(self):
        self.assertEqual(self.host.owner(self.endpoint['owner_id'])['pid'], self.service.process.pid)
        restored = self.backend()
        restored._recover_residencies()
        self.service.process.wait(timeout=5)
        self.assertFalse(self.marker().exists())
        self.assertEqual(self.host.owner(self.endpoint['owner_id'])['state'], 'released')

    def test_pid_reuse_start_identity_mismatch_retains_physical_owner(self):
        marker = json.loads(self.marker().read_text())
        marker['process']['process_start'] = 'incorrect-start'
        self.marker().write_text(json.dumps(marker))
        with self.assertRaisesRegex(SupervisorError, 'recovery_blocked'):
            self.backend()._recover_residencies()
        self.assertIsNone(self.service.process.poll())
        self.assertEqual(self.host.owner(self.endpoint['owner_id'])['state'], 'active')

    def test_foreign_lease_and_failed_wait_or_probe_refuse_reassignment(self):
        for failure in ('lease', 'wait', 'probe'):
            with self.subTest(failure=failure):
                restored = self.backend()
                if failure == 'lease':
                    previous = self.host.metadata[self.endpoint['owner_id']]['project_root']
                    self.host.metadata[self.endpoint['owner_id']]['project_root'] = '/foreign'
                    with self.assertRaisesRegex(SupervisorError, 'recovery_blocked'):
                        restored._recover_residencies()
                    self.host.metadata[self.endpoint['owner_id']]['project_root'] = previous
                elif failure == 'wait':
                    with patch('local_worker.supervisor.terminate_owned', side_effect=ValueError('wait failed')):
                        with self.assertRaisesRegex(SupervisorError, 'recovery_blocked'):
                            restored._recover_residencies()
                else:
                    restored._observe_residency = lambda uuids: {'available': False}
                    with patch('local_worker.supervisor.terminate_owned'):
                        with self.assertRaisesRegex(SupervisorError, 'recovery_blocked'):
                            restored._recover_residencies()
                self.assertTrue(self.marker().exists())
                self.assertIsNone(self.service.process.poll())
                self.assertEqual(self.host.owner(self.endpoint['owner_id'])['state'], 'active')


if __name__ == '__main__':
    unittest.main()
