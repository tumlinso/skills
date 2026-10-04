"""NAT-01..04: native routing, real task context, preserved installed corpus.

No model, GPU, live authority or deployed-PC qualification is exercised here.
"""
from pathlib import Path
import asyncio
import hashlib
import json
import sys
import tempfile
import unittest
import pytest

SKILLS = Path(__file__).resolve().parents[2]
for relative in ('todo-orchestrator', 'todo-orchestrator/tests', 'integrations/coding-workflow-mcp'):
    sys.path.insert(0, str(SKILLS / relative))
from v2_helpers import V2Repo, base_plan, safe_task
from todo_orchestrator.models import TodoError
from coding_workflow_mcp.native_routing import bind_native_routing
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class AS1RoutingAcceptance(unittest.TestCase):
    @pytest.mark.as1_case('NAT-01')
    def test_native_filesystem_routes_and_inactive_fallback_dispatch(self):
        for name in ('cuda', 'cpp-context-compiler', 'local-coding-worker', 'todo-orchestrator'):
            text = (SKILLS / name / 'SKILL.md').read_text()
            self.assertIn('filesystem/command', text)
        cuda = (SKILLS / 'cuda/SKILL.md').read_text()
        self.assertNotIn('skill_context(query=', cuda)
        self.assertNotIn('skill_read(', cuda)
        self.assertIn('mandatory primary skill', cuda)
        server = FastMCP('routing-fixture')
        @server.tool()
        def delegate_task():
            return 'internal-maintenance-preserved'
        @server.tool()
        def coordinate_task():
            return 'normal-context'
        native = bind_native_routing(server)
        async def exercise():
            names = [t.name for t in await native.list_tools()]
            self.assertEqual(names, ['coordinate_task'])
            with self.assertRaises(ToolError):
                await native.call_tool('delegate_task', {})
            self.assertTrue(await native.call_tool('coordinate_task', {}))
            self.assertTrue(await server.call_tool('delegate_task', {}))
        asyncio.run(exercise())

    @pytest.mark.as1_case('NAT-02')
    def test_normal_task_publication_distinguishes_applied_and_consulted(self):
        repo = V2Repo()
        self.addCleanup(repo.close)
        repo.apply(base_plan([safe_task('A', 'src/a')]))
        source = repo.root / 'src/a/contract.txt'
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text('canonical route result\n')
        service = repo.service
        token = service.continue_work(task_id='A')['claim']['claim_token']
        payload = {'id':'cuda-route', 'skill':'cuda', 'skill_sha256':sha(SKILLS/'cuda/SKILL.md'),
                   'status':'consulted', 'task':'A', 'route':'volta/routes/hot-kernel',
                   'reason':'Read guidance before deciding the owned contract',
                   'anchors':[{'project':service.project['project_uuid'],
                               'repository':str(repo.root), 'path':'src/a/contract.txt',
                               'content_sha256':sha(source)}]}
        def publish():
            return service.publish_project_context({'kind':'skill_use','task_id':'A','payload':payload},claim_token=token)
        self.assertEqual(publish()['status'], 'published')
        self.assertEqual(service.project_context()['skill_uses'][0]['payload']['status'], 'consulted')
        payload['status']='applied'
        payload['reason']='Applied Volta hot-kernel guidance to the owned contract'
        publish()
        use=service.project_context()['skill_uses'][0]
        self.assertEqual(use['payload']['status'], 'applied')
        self.assertEqual(use['task_id'], 'A')
        self.assertEqual(use['payload']['skill_sha256'], sha(SKILLS/'cuda/SKILL.md'))
        self.assertEqual(publish()['status'], 'noop')
        source.write_text('changed canonical result\n')
        with self.assertRaises(TodoError):
            publish()

    @pytest.mark.as1_case('NAT-03')
    def test_every_captured_cuda_ctxpp_technical_resource_is_identical(self):
        baseline=json.loads((SKILLS/'planning/adaptive-surface-v1/validation/routing-corpus-baseline.json').read_text())
        self.assertGreater(len(baseline['files']), 400)
        for relative, expected in baseline['files'].items():
            with self.subTest(resource=relative):
                self.assertEqual(sha(SKILLS/relative), expected)
        # Untracked source-only observations must not become product dependencies.
        def verify_optional(path, expected):
            if not path.exists():
                return 'absent-source-only'
            self.assertEqual(sha(path), expected)
            return 'verified-source-only'
        for relative, expected in baseline['optional_source_only_observations'].items():
            with self.subTest(source_only=relative):
                verify_optional(SKILLS/relative, expected)
        with tempfile.TemporaryDirectory() as directory:
            observation=Path(directory)/'optional-AppleDouble'
            self.assertEqual(verify_optional(observation, hashlib.sha256(b'original').hexdigest()),
                             'absent-source-only')
            observation.write_bytes(b'original')
            self.assertEqual(verify_optional(observation, sha(observation)), 'verified-source-only')
            with self.assertRaises(AssertionError):
                verify_optional(observation, hashlib.sha256(b'changed').hexdigest())
        for marker in ('V100_ATLAS_FULL.md', 'ledger/claims.jsonl', 'manifest.json', '.zip'):
            self.assertTrue(any(marker in p for p in baseline['files']), marker)

    @pytest.mark.as1_case('NAT-04')
    def test_catalog_covers_installed_entries_and_nested_native_routes(self):
        catalog=json.loads((SKILLS/'integrations/native-skill-catalog.json').read_text())
        installed={p.parent.name for p in SKILLS.glob('*/SKILL.md')}
        self.assertEqual({e['name'] for e in catalog['entries']}, installed)
        for entry in catalog['entries']:
            self.assertEqual(entry['status'], 'accessible')
            self.assertEqual(sha(SKILLS/entry['entry']), entry['sha256'])
            for route in entry['routes']:
                path=SKILLS/entry['name']/route['path']
                self.assertEqual(route['status'], 'accessible' if path.is_file() else 'missing')
                if path.is_file():
                    self.assertTrue(path.read_text().strip())
        cuda=next(e for e in catalog['entries'] if e['name']=='cuda')
        self.assertTrue(any('v100_atlas/NEED_INDEX.md' in p['path'] for p in cuda['routes']))
        authored_maps={str(p.relative_to(SKILLS/'cuda')) for p in (SKILLS/'cuda').rglob('router.md')}
        authored_maps.update(str(p.relative_to(SKILLS/'cuda')) for p in (SKILLS/'cuda').glob('references/architectures/*/routes/*.md'))
        self.assertTrue(authored_maps <= {p['path'] for p in cuda['routes']})
        self.assertEqual(catalog['external_dependencies'][0]['status'], 'missing')
        self.assertFalse((SKILLS/catalog['external_dependencies'][0]['name']/ 'SKILL.md').exists())
        self.assertTrue(catalog['unsupported'])
        self.assertIn('absent map', (SKILLS/'integrations/native-skill-routing.md').read_text())


if __name__ == '__main__':
    unittest.main()
