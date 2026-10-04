"""Subprocess journeys: candidate-only imports, no pytest dependency."""
import asyncio
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
SKILLS = Path(__file__).resolve().parents[2]
CANDIDATE = Path(os.environ['AS1_SQA_CANDIDATE'])
SK_COMMIT = os.environ['AS1_SQA_SK_COMMIT']
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def committed_package_fingerprint(repository, commit, prefix):
    archive = subprocess.check_output(['git', '-C', str(repository), 'archive', commit, prefix])
    with tarfile.open(fileobj=io.BytesIO(archive)) as tree:
        members = sorted((member for member in tree.getmembers()
                          if member.isfile() and member.name.endswith('.py')), key=lambda member: member.name)
        assert members
        digest = hashlib.sha256()
        for member in members:
            relative = Path(member.name).relative_to(prefix).as_posix()
            digest.update(relative.encode()); digest.update(b'\0')
            digest.update(tree.extractfile(member).read()); digest.update(b'\0')
        return digest.hexdigest()

def child(journey, scratch):
    """Import only installed candidate packages, with genuine release binding."""
    from project_control.runtime_identity import bind_runtime, validate_runtime, package_fingerprint
    from project_control.workflow_binding import initialize_workflow_binding
    from project_control.app import create_mcp
    from project_control.config import ProjectControlConfig
    from project_control.profiles import enumerate_tool_schemas
    from todo_orchestrator.service import Service
    from todo_orchestrator.models import TodoError
    import project_control
    import todo_orchestrator

    release = json.loads((CANDIDATE / 'release-manifest.json').read_text())
    identity = bind_runtime()
    assert identity.release_digest == sha(CANDIDATE / 'release-manifest.json')
    assert Path(todo_orchestrator.__file__).resolve().is_relative_to(CANDIDATE)
    assert Path(project_control.__file__).resolve().is_relative_to(CANDIDATE)
    assert package_fingerprint(Path(project_control.__file__).parent) == release['project_control_fingerprint']
    assert release['project_control_fingerprint'] == committed_package_fingerprint(
        Path('/home/tumlinson/project-control'), release['project_control_commit'], 'src/project_control')
    assert identity.fingerprint == committed_package_fingerprint(
        SKILLS, SK_COMMIT, 'todo-orchestrator/todo_orchestrator')
    observer_package = identity.skills_root / 'local-coding-worker/local_worker'
    observer_fingerprint = committed_package_fingerprint(
        SKILLS, SK_COMMIT, 'local-coding-worker/local_worker')
    assert package_fingerprint(observer_package) == observer_fingerprint
    assert release['observer_analysis_binding']['fingerprint'] == observer_fingerprint
    observer_runtime = 'local-coding-worker/local_worker/observer_runtime.py'
    assert (identity.skills_root / observer_runtime).read_bytes() == subprocess.check_output([
        'git', '-C', str(SKILLS), 'show', SK_COMMIT + ':' + observer_runtime])
    validate_runtime(identity)
    binding = initialize_workflow_binding()
    contract = json.loads((SKILLS / 'planning/adaptive-surface-v1/contracts/surface.json').read_text())
    servers = []
    try:
        roles = ['observer', 'investigator', 'skill_assembler', 'coder', 'codex', 'mutator']
        for role in roles:
            server = create_mcp(ProjectControlConfig(), profile=role, state_directory=scratch / role)
            servers.append(server)
            schemas = asyncio.run(enumerate_tool_schemas(server))
            canonical_role = {'codex': 'coder', 'skill_assembler': 'investigator'}.get(role, role)
            assert set(schemas) == set(contract['profiles'][canonical_role]['tools'])
            from mcp.server.fastmcp.exceptions import ToolError
            for forbidden in ('delegate_task', 'collect_delegation'):
                try:
                    asyncio.run(server.call_tool(forbidden, {}))
                except ToolError:
                    pass
                else:
                    raise AssertionError('Inactive coding delegation dispatched')
        if journey == 'delegation':
            # Exercise preserved native implementation validation, independently
            # of the public guard. No delegate or model/GPU is started.
            try:
                binding.protocol.delegate_task(workflow_handle='invalid', delegated_objective='fixture', mode='forbidden')
            except TodoError as exc:
                assert exc.code == 'invalid_delegation_mode'
            else:
                raise AssertionError('Native delegation validator disappeared')
            try:
                binding.protocol.collect_delegation(delegation_handle='invalid')
            except TodoError:
                pass
            else:
                raise AssertionError('Native collection accepted invalid capability')
            return {'status': 'passed'}
        if journey == 'workflow':
            from todo_orchestrator.read_port import create_todo_read_port
            port = create_todo_read_port(identity.skills_root)
            # Canonical authority observations open read-only; no Service writer
            # or bootstrap ever targets these registered source repositories.
            os.environ.pop('XDG_STATE_HOME', None)
            operations = ['status', 'ready', 'semantic.state', 'semantic.workflow']
            for root in (SKILLS, Path('/home/tumlinson/project-control')):
                for operation in operations:
                    observation = port.invoke(operation, repo_root=root)
                    assert observation['ok'], (root, operation, observation)
            os.environ['TODO_ORCHESTRATOR_STATE_DIR'] = str(scratch / 'fixture-state')
            root = scratch / 'repo'; root.mkdir()
            subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
            service, _ = Service.bootstrap(root, 'sqa-fixture')
            plan = {'schema_version': 2, 'project': {'name': 'sqa-fixture'}, 'tasks': [
                {'id': 'SQA-FIXTURE', 'kind': 'task', 'title': 'Qualification fixture',
                 'objective': 'Complete disposable workflow', 'parallel_policy': 'parallel_safe',
                 'scope': {'exclusive_paths': ['owned']}}]}
            planpath = root / 'plan.json'; planpath.write_text(json.dumps(plan))
            service.plan_apply(str(planpath))
            claim = binding.protocol.next_task(repo_root=str(root), task_id='SQA-FIXTURE')
            handle = claim['workflow_handle']
            binding.protocol.inspect_task(workflow_handle=handle, kind='task')
            binding.protocol.finish_task(workflow_handle=handle, action='complete', disposition='validated', note='Disposable qualification')
            assert service.explain('SQA-FIXTURE')['lifecycle'] == 'done'
            return {'status': 'passed', 'canonical_reads': operations, 'fixture_completion': 'done',
                    'roles': roles}
        assert journey == 'provenance'
        catalog = servers[0]._project_control_surface.skills.catalog(
            access_scope=servers[0]._project_control_surface.host.scope(None))
        assert catalog['status'] == 'ok' and catalog['complete'], catalog
        rows = {row['name']: row for row in catalog['skills']}
        for name in ('cuda', 'cpp-context-compiler', 'todo-orchestrator', 'local-coding-worker'):
            assert rows[name]['status'] == 'accessible'
            assert rows[name]['content_sha256'] == sha(identity.skills_root / name / 'SKILL.md')
        receipt_path = 'planning/adaptive-surface-v1/validation/skills-routing-producer-receipt.json'
        raw = subprocess.check_output(['git', '-C', str(SKILLS), 'show', SK_COMMIT + ':' + receipt_path])
        receipt = json.loads(raw)
        assert receipt['project'] == 'skills' and receipt['task'] == 'SK-AS1-ROUTING'
        assert receipt['run'] == 'SK-AS1-RUN-1'
        assert Path(receipt['source']['repository']).resolve() == SKILLS
        assert receipt['native_acceptance']['status'] == 'completed_validated'
        assert receipt['native_acceptance']['evidence_id']
        assert {case['id'] for case in receipt['native_acceptance']['cases']} == {
            'NAT-01', 'NAT-02', 'NAT-03', 'NAT-04'}
        producer = receipt['source']['commit']
        for relative, expected in receipt['source']['files_sha256'].items():
            source = subprocess.check_output(['git', '-C', str(SKILLS), 'show', producer + ':' + relative])
            assert hashlib.sha256(source).hexdigest() == expected
            if relative.endswith('/SKILL.md') or relative in (
                    'integrations/native-skill-catalog.json', 'integrations/native-skill-routing.md'):
                installed = identity.skills_root / relative
                assert installed.is_file(), ('Producer resource missing from candidate', relative)
                assert sha(installed) == expected, ('Installed producer contract differs', relative)
        for relative in ('integrations/native-skill-catalog.json', 'integrations/native-skill-routing.md'):
            committed = subprocess.check_output(['git', '-C', str(SKILLS), 'show', SK_COMMIT + ':' + relative])
            installed = identity.skills_root / relative
            assert installed.read_bytes() == committed
            assert release['frozen_skill_resources'][relative] == sha(installed)
        # Actual installed native files remain the authority, catalog is only
        # navigation. Record exact route hashes with fixture source-backed use.
        os.environ['TODO_ORCHESTRATOR_STATE_DIR'] = str(scratch / 'fixture-state')
        root = scratch / 'repo'; root.mkdir()
        subprocess.run(['git', '-C', str(root), 'init', '-q'], check=True)
        service, _ = Service.bootstrap(root, 'sqa-provenance')
        entry = identity.skills_root / 'cuda/SKILL.md'
        assert entry.read_bytes() == subprocess.check_output([
            'git', '-C', str(SKILLS), 'show', SK_COMMIT + ':cuda/SKILL.md'])
        assert 'filesystem/command' in entry.read_text()
        route = identity.skills_root / 'cuda/references/architectures/volta/routes/hot-kernel.md'
        assert route.is_file() and route.read_text().strip()
        source = root / 'route.txt'; source.write_text('Used installed native route\n')
        payload = {'id': 'sqa-route', 'skill': 'cuda', 'skill_sha256': sha(entry),
                   'status': 'consulted', 'route': str(route.relative_to(identity.skills_root / 'cuda')),
                   'reason': 'Exact native route consulted', 'anchors': [{
                       'project': service.project['project_uuid'], 'repository': str(root),
                       'path': 'route.txt', 'content_sha256': sha(source)}]}
        request = {'format': 'pc-project-amendment/1', 'project': service.project['project_uuid'],
                   'action': 'record_skill_use', 'intent': 'Qualify installed native provenance',
                   'expected_revision': service.db.revision(),
                   'operation_id': 'sqa-consult-operation', 'payload': payload}
        service.amend_project(request, role='mutator')
        use = service.project_context()['skill_uses'][0]
        assert use['payload']['skill_sha256'] == sha(entry)
        assert use['payload']['status'] == 'consulted'
        request['operation_id'] = 'sqa-applied-operation'
        request['expected_revision'] = service.db.revision()
        payload['status'] = 'applied'
        service.amend_project(request, role='mutator')
        applied = service.project_context()['skill_uses'][0]
        assert applied['payload']['status'] == 'applied'
        assert applied['payload']['route'] == str(route.relative_to(identity.skills_root / 'cuda'))
        assert applied['payload']['anchors'][0]['content_sha256'] == sha(source)
        source.write_text('Changed owned result invalidates prior source proof\n')
        request['operation_id'] = 'sqa-stale-operation'
        request['expected_revision'] = service.db.revision()
        before = service.db.revision()
        try:
            service.amend_project(request, role='mutator')
        except TodoError:
            pass
        else:
            raise AssertionError('Stale source became current applied skill proof')
        assert service.db.revision() == before
        return {'status': 'passed'}
    finally:
        for server in servers:
            server._project_control_surface.close()


if __name__ == '__main__':
    assert len(sys.argv) == 4 and sys.argv[1] == '--journey'
    print(json.dumps(child(sys.argv[2], Path(sys.argv[3]))))
