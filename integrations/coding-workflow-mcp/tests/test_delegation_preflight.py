from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


SKILLS = Path(__file__).resolve().parents[3]
WORKER_ROOT = SKILLS / "local-coding-worker"
for item in (WORKER_ROOT, SKILLS / "todo-orchestrator"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from local_worker.controller import IntegrationController  # noqa: E402


def cli_module():
    scripts = WORKER_ROOT / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location("cwm_preflight_worker_cli", scripts / "local_worker.py")
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module
    finally:
        if str(scripts) in sys.path:
            sys.path.remove(str(scripts))


class DelegationPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "src").mkdir()
        (self.root / "src/widget.cpp").write_text("int widget() { return 7; }\n", encoding="utf-8")
        (self.root / ".ctxpp.toml").write_text("version = 1\nprofile = \"model\"\n", encoding="utf-8")
        self.log = Path(self.temporary.name) / "ctxpp.log"
        self.fake_ctxpp = Path(self.temporary.name) / "fake_ctxpp.py"
        self.fake_ctxpp.write_text(
            "#!/usr/bin/env python3\n"
            "import fcntl,hashlib,json,os,sys,time\n"
            "from pathlib import Path\n"
            "args=sys.argv[1:]; root=Path(args[args.index('--root')+1]); command=next(x for x in ('packet','init','scan') if x in args)\n"
            "log=Path(os.environ['CWM_CTXPP_LOG']); log.parent.mkdir(parents=True,exist_ok=True)\n"
            "with log.open('a') as stream:\n"
            " fcntl.flock(stream.fileno(),fcntl.LOCK_EX); stream.write(command+'\\n'); stream.flush(); fcntl.flock(stream.fileno(),fcntl.LOCK_UN)\n"
            "index=root/'.fake-semantic-index'\n"
            "if command=='init': print(json.dumps({'format':'CTXPP-INIT/1','ok':True})); raise SystemExit(0)\n"
            "if command=='scan':\n"
            " time.sleep(0.15); index.write_text('semantic'); print(json.dumps({'format':'CTXPP-SCAN/1','backend':'semantic','failures':0})); raise SystemExit(0)\n"
            "if not index.is_file(): print('ctxpp: semantic index missing; run ctxpp scan',file=sys.stderr); raise SystemExit(2)\n"
            "if os.environ.get('CWM_CTXPP_ALWAYS_FAIL')=='1': print('ctxpp: packet construction failed',file=sys.stderr); raise SystemExit(2)\n"
            "spec=json.loads(Path(args[args.index('--task-spec')+1]).read_text()); source=root/'src/widget.cpp'; digest=hashlib.sha256(source.read_bytes()).hexdigest()\n"
            "packet={'format':'CTXPP-CONTEXT-PACKET/2','schema_version':2,'readonly':True,'consumer':'local-worker','task_spec':spec,'request':{'intent':spec['role'],'budget_tokens':4096,'max_items':12,'target_count':1},'source_identity':{'fingerprint':'b'*64},'canonical_targets':[{'canonical':True,'id':'widget','kind':'FunctionDecl','name':'widget','signature':'int widget()','content':'int widget() { return 7; }','location':{'path':'src/widget.cpp','line':1,'end_line':1,'byte_start':0,'byte_end':26,'content_sha256':digest}}],'semantic_support':{},'invariants':[],'trust':{'sufficient_for':[spec['role']],'missing_required':[],'omitted_optional':{},'confidence':'high','freshness':'hash-verified','source_authority':'canonical-repository-source','relationships':'semantic'},'expansions':[],'budget_exceeded':False,'estimated_tokens':128}\n"
            "packet['packet_hash']=hashlib.sha256(json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(); print(json.dumps(packet,sort_keys=True,separators=(',',':')))\n",
            encoding="utf-8",
        )
        self.fake_ctxpp.chmod(0o755)
        self.environment = {"CWM_CTXPP_LOG": str(self.log)}

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, mode: str = "readonly") -> dict[str, object]:
        common: dict[str, object] = {
            "format": "CORE4-INTEGRATION-REQUEST/2", "schema_version": 2,
            "mode": mode, "repo_root": str(self.root), "parent_claim_token": "toc_fixture",
            "task_id": "FIXTURE", "objective": "Review widget in src/widget.cpp.",
            "scopes": ["src"], "gates": [],
            "execution": {"backend": "real", "harness": "qwen", "gpu_count": 1},
        }
        if mode == "readonly":
            common.update(role="review", target="src/widget.cpp", intent="understand",
                          budget_tokens=4096, max_items=12)
        else:
            command = {"schema_version": 1, "argv": [sys.executable, "-c", "pass"],
                       "cwd": ".", "env": {}, "timeout_seconds": 30}
            common.update(target="src/widget.cpp", read_dependencies=[], approved_overlays=[],
                          baseline_commands=[command], verification_commands=[command],
                          acceptance_commands=[command])
        return common

    def controller(self, **environment: str) -> IntegrationController:
        return IntegrationController(
            ctxpp_cli=self.fake_ctxpp,
            environment={**self.environment, **environment},
        )

    def operations(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def test_uninitialized_configured_repository_is_prepared_before_admission(self) -> None:
        prepared = self.controller().prepare_delegation(self.request())
        self.assertEqual(prepared["context_packet"]["format"], "CTXPP-CONTEXT-PACKET/2")
        self.assertEqual(self.operations().count("init"), 1)
        self.assertEqual(self.operations().count("scan"), 1)
        self.assertEqual(self.operations().count("packet"), 2)

    def test_writable_preflight_proves_packet_before_any_model_path(self) -> None:
        prepared = self.controller().prepare_delegation(self.request("writable"))
        self.assertEqual(prepared["context_packet"]["trust"]["sufficient_for"], ["edit"])
        self.assertEqual(prepared["context_packet"]["canonical_targets"][0]["location"]["path"],
                         "src/widget.cpp")
        self.assertEqual(self.operations().count("scan"), 1)

    def test_real_ctxpp_initializes_and_builds_usable_bounded_packet(self) -> None:
        fixture = Path(self.temporary.name) / "semantic-repo"
        shutil.copytree(SKILLS / "cpp-context-compiler/tests/fixtures/sample", fixture)
        subprocess.run([
            "cmake", "-S", str(fixture), "-B", str(fixture / "build"),
            "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
        ], check=True, stdout=subprocess.DEVNULL)
        (fixture / "compile_commands.json").symlink_to("build/compile_commands.json")
        subprocess.run(["git", "init", "-q"], cwd=fixture, check=True)
        request = self.request()
        request.update(
            repo_root=str(fixture), scopes=["src", "include"],
            target="src/plan.cpp",
            objective="Review PackingPlan freeze implementation in src/plan.cpp.",
        )
        controller = IntegrationController(
            ctxpp_cli=SKILLS / "cpp-context-compiler/scripts/ctxpp",
        )
        prepared = controller.prepare_delegation(request)
        packet = prepared["context_packet"]
        self.assertTrue((fixture / ".ctxpp/index.jsonl").is_file())
        self.assertIn("review", packet["trust"]["sufficient_for"])
        self.assertTrue(packet["canonical_targets"])
        self.assertTrue(all(
            target["location"]["path"].startswith(("src/", "include/"))
            for target in packet["canonical_targets"]
        ))

    def test_two_concurrent_first_delegations_share_one_initialization(self) -> None:
        module = cli_module()
        barrier = threading.Barrier(2)
        admission_lock = threading.Lock()
        admissions: list[str] = []

        class Supervisor:
            def request(inner_self, operation, **parameters):
                self.assertEqual(operation, "admit")
                with admission_lock:
                    admission = f"admission-{len(admissions) + 1}"
                    admissions.append(admission)
                return {"status": "admitted", "admission_id": admission}

        results: list[dict[str, object]] = []
        failures: list[BaseException] = []

        def launch(index: int) -> None:
            controller = self.controller()
            controller.request_from_claim = mock.Mock(return_value=self.request())
            try:
                barrier.wait()
                results.append(module._launch_delegate(
                    self.root, f"toc_fixture_{index}", "readonly", None,
                    controller=controller, supervisor=Supervisor(),
                ))
            except BaseException as error:
                failures.append(error)

        original_popen = subprocess.Popen
        pids = iter((101, 102))
        def popen(argv, *args, **kwargs):
            if "_delegate-worker" in argv:
                return type("LaunchProcess", (), {"pid": next(pids)})()
            return original_popen(argv, *args, **kwargs)

        with mock.patch.object(module, "runtime_root", return_value=Path(self.temporary.name) / "runtime"), \
                mock.patch.object(module.subprocess, "Popen", side_effect=popen):
            threads = [threading.Thread(target=launch, args=(index,)) for index in range(2)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=10)
        self.assertFalse(failures)
        self.assertEqual([result["status"] for result in results], ["delegated", "delegated"])
        self.assertEqual(len(admissions), 2)
        self.assertEqual(self.operations().count("init"), 1)
        self.assertEqual(self.operations().count("scan"), 1)
        requests = list(((Path(self.temporary.name) / "runtime/delegations").glob("*.request.json")))
        self.assertEqual(len(requests), 2)
        self.assertTrue(all("context_packet" in json.loads(path.read_text())["request"] for path in requests))

    def test_preflight_failure_creates_no_admission_child_scope_or_model(self) -> None:
        module = cli_module()
        controller = self.controller(CWM_CTXPP_ALWAYS_FAIL="1")
        controller.request_from_claim = mock.Mock(return_value=self.request())

        class Supervisor:
            def request(inner_self, operation, **parameters):
                raise AssertionError("preflight failure must precede admission")

        original_popen = subprocess.Popen
        def refuse_launch(argv, *args, **kwargs):
            if "_delegate-worker" in argv:
                raise AssertionError("model worker must not launch")
            return original_popen(argv, *args, **kwargs)
        with mock.patch.object(module, "runtime_root", return_value=Path(self.temporary.name) / "runtime"), \
                mock.patch.object(module.subprocess, "Popen", side_effect=refuse_launch):
            result = module._launch_delegate(
                self.root, "toc_fixture", "readonly", None,
                controller=controller, supervisor=Supervisor(),
            )
        self.assertEqual(result["status"], "not_eligible")
        self.assertFalse(result["child_created"])
        self.assertFalse(result["scope_locked"])
        self.assertFalse(result["admission_created"])
        self.assertFalse(result["model_started"])
        self.assertFalse((Path(self.temporary.name) / "runtime/delegations").exists())


if __name__ == "__main__":
    unittest.main()
