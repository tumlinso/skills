from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SKILLS = SKILL.parent
for item in (SKILL, SKILLS / "todo-orchestrator"):
    if str(item) not in sys.path:
        sys.path.insert(0, str(item))

from local_worker.controller import IntegrationController, ProductionReadOnlyRuntime


def command(code: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "argv": [sys.executable, "-c", code],
        "cwd": ".",
        "timeout_seconds": 20,
    }


class Core4IntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.root.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "core4@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "CORE4 Test"], cwd=self.root, check=True)
        (self.root / "src").mkdir()
        (self.root / "docs").mkdir()
        (self.root / "src/kernel.cu").write_text("// baseline\n", encoding="utf-8")
        (self.root / "docs/note.txt").write_text("stable\n", encoding="utf-8")
        self.registry = self.root / "cuda-benchmarks.json"
        self.registry.write_text(json.dumps({
            "format": "CUDA-BENCHMARK-REGISTRY/1",
            "schema_version": 1,
            "project_root": str(self.root),
            "campaigns": [{
                "id": "fixture-sm70",
                "description": "Fixture discovery only",
                "targets": [],
                "paths": ["src/**/*.cu"],
                "symbols": [],
                "task_ids": [],
                "task_prefixes": [],
                "build": None,
                "correctness": {"argv": [sys.executable, "-c", "assert True"], "repetitions": 1},
                "benchmark": {"argv": [sys.executable, "-c", "print('{\\\"latency_ms\\\":1}')"], "warmups": 0, "repetitions": 1},
                "metric": {"format": "CUDA-METRIC/1", "schema_version": 1, "name": "latency_ms",
                           "path": "latency_ms", "direction": "minimize", "unit": "ms",
                           "practical_regression_percent": 2.0, "target": None},
                "resources": {"gpu_count": 1, "architecture": "volta"},
                "policy": {"initial_characterization": False},
            }],
        }), encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "baseline"], cwd=self.root, check=True)

        self.state = Path(self.temporary.name) / "todo-state.json"
        self.state.write_text(json.dumps({"state": "running", "result": None}), encoding="utf-8")
        self.fake_todo = Path(self.temporary.name) / "fake_todo.py"
        self.fake_todo.write_text(
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "from pathlib import Path\n"
            "args=sys.argv[1:]; path=Path(os.environ['CORE4_FAKE_TODO_STATE']); state=json.loads(path.read_text())\n"
            "data={}\n"
            "if args[:2]==['child','create']:\n"
            " data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':'running','child_token':'toch_fixture'}\n"
            "elif args[:2]==['child','heartbeat']:\n"
            " data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':'running'}\n"
            "elif args[:2]==['child','report']:\n"
            " status=args[args.index('--status')+1]; changed=[args[i+1] for i,v in enumerate(args) if v=='--changed-path']; state={'state':status,'result':{'status':status,'changed_paths':changed}}; path.write_text(json.dumps(state)); data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':status,'result':state['result']}\n"
            "elif args[:2]==['child','status']:\n"
            " data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':state['state'],'result':state['result']}\n"
            "elif len(args)>1 and args[0]=='child' and args[1] in {'accept','reject','stale','supersede'}:\n"
            " target={'accept':'accepted','reject':'rejected','stale':'stale','supersede':'stale'}[args[1]]; state={'state':target,'result':state['result']}; path.write_text(json.dumps(state)); data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':target}\n"
            "elif args[:2]==['child','cancel']:\n"
            " state={'state':'canceled','result':None}; path.write_text(json.dumps(state)); data={'child_execution_id':'child-fixture','task_id':os.environ['CORE4_FAKE_TASK_ID'],'state':'canceled'}\n"
            "else: raise SystemExit(3)\n"
            "print(json.dumps({'ok':True,'data':data}))\n",
            encoding="utf-8",
        )
        os.chmod(self.fake_todo, 0o755)
        self.fake_ctxpp = Path(self.temporary.name) / "fake_ctxpp.py"
        self.fake_ctxpp.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib,json,sys\n"
            "from pathlib import Path\n"
            "root=Path(sys.argv[sys.argv.index('--root')+1]); target=sys.argv[sys.argv.index('packet')+1]; source=root/'src/kernel.cu'; complete=target!='needs'\n"
            "packet={'format':'CTXPP-CONTEXT-PACKET/1','readonly':True,'target':{'id':'kernel','name':target,'signature':target,'location':{'path':'src/kernel.cu','line':1,'end_line':1,'content_sha256':hashlib.sha256(source.read_bytes()).hexdigest()}},'trust':{'target_range':'hash-verified','relationships':'semantic' if complete else 'lexical-or-partial','index_incomplete':not complete},'coverage':{'sufficient':complete},'packet_hash':'a'*64,'source_identity':{'schema_version':1,'repo_root':str(root),'git_head':None,'dirty_paths':[],'fingerprint':'b'*64},'estimated_tokens':96}\n"
            "print(json.dumps(packet))\n",
            encoding="utf-8",
        )
        os.chmod(self.fake_ctxpp, 0o755)
        self.environment = {
            "CORE4_FAKE_TODO_STATE": str(self.state),
            "CORE4_FAKE_TASK_ID": "CORE4-FIXTURE",
        }

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def controller(self, **kwargs) -> IntegrationController:
        return IntegrationController(
            todo_cli=self.fake_todo,
            ctxpp_cli=self.fake_ctxpp,
            environment=self.environment,
            **kwargs,
        )

    def request(self, mode: str, **updates) -> dict[str, object]:
        common: dict[str, object] = {
            "format": "CORE4-INTEGRATION-REQUEST/1",
            "schema_version": 1,
            "mode": mode,
            "repo_root": str(self.root),
            "parent_claim_token": "toc_fixture",
            "task_id": "CORE4-FIXTURE",
            "objective": "Perform one bounded fake-backend child execution.",
            "scopes": ["src"],
            "gates": [],
            "cuda_registry": str(self.registry),
        }
        if mode == "readonly":
            common.update(role="review", target="kernel", intent="understand", budget_tokens=1024, max_items=8)
        else:
            common.update(
                fake_changes={"src/kernel.cu": "// accepted candidate\n"},
                baseline_commands=[command("from pathlib import Path; assert Path('src/kernel.cu').read_text() == '// baseline\\n'")],
                verification_commands=[command("from pathlib import Path; assert 'candidate' in Path('src/kernel.cu').read_text()")],
                acceptance_commands=[command("from pathlib import Path; assert 'candidate' in Path('src/kernel.cu').read_text()")],
            )
        common.update(updates)
        return common

    def test_readonly_flow_is_terminal_and_healthy_evidence_is_silent(self) -> None:
        before = (self.root / "src/kernel.cu").read_bytes()
        result = self.controller().run(self.request("readonly"))
        self.assertEqual(result["status"], "no_change")
        self.assertEqual(result["child_state"], "succeeded")
        self.assertEqual(result["changed_paths"], [])
        self.assertEqual(result["cuda"], {"state": "silent", "campaign_ids": []})
        self.assertEqual((self.root / "src/kernel.cu").read_bytes(), before)
        self.assertFalse(result["parent_task_completed"])

    def test_needs_codex_is_a_successful_terminal_handback(self) -> None:
        result = self.controller().run(self.request("readonly", target="needs"))
        self.assertEqual(result["status"], "needs_codex")
        self.assertEqual(result["child_state"], "needs_codex")
        self.assertFalse(result["accepted"])

    def test_v2_integration_forwards_policy_selected_real_execution(self) -> None:
        seen = {}
        def terminal(request):
            seen.update(request)
            return {"status": "completed", "summary": "bounded", "changed_paths": [],
                    "child_reported": False, "packet_hash": "a" * 64, "artifacts": []}
        request = self.request("readonly")
        request.update(format="CORE4-INTEGRATION-REQUEST/2", schema_version=2,
                       execution={"backend": "real", "harness": "qwen", "gpu_count": 1})
        result = self.controller(terminal_runner=terminal).run(request)
        self.assertEqual(result["status"], "completed")
        self.assertEqual((seen["format"], seen["backend"]), ("LCW-REQUEST/2", "real"))

    def test_production_runtime_composes_cache_gpu_service_harness_and_cleanup(self) -> None:
        events = []
        profile = {"deployment_policy": {"real_local_enabled": True, "hot_idle_seconds": 0},
                   "server": {"split_mode": "layer", "base_port": 8080, "startup_timeout_seconds": 5},
                   "experiment": {"initial_context": 16384}, "harnesses": {"qwen": "qwen", "codex": "codex"},
                   "storage": {"cache_root": "/cache", "canonical_root": "/cold"}}
        class Cache:
            root = Path(self.temporary.name)
            def active(self): return {"candidate_id": "candidate", "payload_sha256": "a" * 64}
            def verify(self, *args, **kwargs): return {"payload_path": "/external/model.gguf"}
            @contextmanager
            def lease(self, *args): events.append("lease"); yield Path("/external/model.gguf"); events.append("unlease")
        class Host:
            def discover_gpus(self): events.append("discover")
            def compound_gpu_bundles(self, count): return [{"resource_ids": ["accelerator:GPU-a"], "exclusive_resources": []}]
            def reserve_service(self, **kwargs): events.append("reserve"); return {"owner_id": "owner", "resource_ids": ["accelerator:GPU-a"]}
            def release(self, owner): events.append("release")
        class Runtime: host = Host()
        class Service:
            def start(self, name, context): events.append(("server-start", context["service_profile"]["allocated_gpu_uuids"])); return "server"
            def evict(self, name, handle): events.append("server-evict")
        class Harness:
            def start(self, context): events.append("harness-start"); return "harness"
            def run(self, handle, request): events.append("harness-run"); return {"status": "succeeded", "text": "done", "usage": {"core4": {"tool_calls": 2}}, "duration_ms": 1}
            def evict(self, handle): events.append("harness-evict")
        runtime = ProductionReadOnlyRuntime(profile=profile, cache=Cache(), runtime=Runtime(), service=Service(),
                                            harness_factory=lambda name: Harness())
        snapshot = type("Snapshot", (), {"root": self.root})()
        request = {"repo_root": str(self.root), "objective": "bounded", "execution": {"backend": "real", "harness": "qwen", "gpu_count": 1}}
        result = runtime.execute(request, {"format": "CTXPP-CONTEXT-PACKET/2"}, snapshot)
        self.assertEqual((result["status"], result["tool_calls"]), ("completed", 2))
        self.assertIn(("server-start", ["GPU-a"]), events)
        self.assertEqual(events[-3:], ["harness-evict", "server-evict", "release"])

    def test_preempted_terminal_worker_returns_needs_codex_without_source_change(self) -> None:
        before = (self.root / "src/kernel.cu").read_bytes()
        terminal = lambda request: {
            "status": "needs_codex", "summary": "resource_preempted",
            "changed_paths": [], "child_reported": False,
        }
        result = self.controller(terminal_runner=terminal).run(self.request("readonly"))
        self.assertEqual(result["status"], "needs_codex")
        self.assertIn("preempted", result["summary"])
        self.assertEqual((self.root / "src/kernel.cu").read_bytes(), before)

    def test_writable_patch_is_externally_verified_guarded_and_triggers_cuda(self) -> None:
        result = self.controller().run(self.request("writable"))
        self.assertEqual(result["status"], "accepted")
        self.assertTrue(result["accepted"])
        self.assertEqual(result["changed_paths"], ["src/kernel.cu"])
        self.assertEqual(result["cuda"]["state"], "triggered")
        self.assertEqual(result["cuda"]["campaign_ids"], ["fixture-sm70"])
        self.assertEqual((self.root / "src/kernel.cu").read_text(encoding="utf-8"), "// accepted candidate\n")
        self.assertFalse(result["parent_task_completed"])

    def test_stale_patch_is_rejected_without_overwriting_concurrent_user_change(self) -> None:
        def make_stale(root: Path, artifact: dict[str, object]) -> None:
            (root / "docs/note.txt").write_text("concurrent user work\n", encoding="utf-8")

        result = self.controller(before_accept=make_stale).run(self.request("writable"))
        self.assertEqual(result["status"], "stale_patch")
        self.assertFalse(result["accepted"])
        self.assertEqual((self.root / "src/kernel.cu").read_text(encoding="utf-8"), "// baseline\n")
        self.assertEqual((self.root / "docs/note.txt").read_text(encoding="utf-8"), "concurrent user work\n")
        self.assertEqual(result["cuda"]["state"], "silent")

    def test_v2_writable_runner_uses_approved_overlay_and_persists_reviewer_evidence(self) -> None:
        (self.root / "docs/note.txt").write_text("unrelated user work\n", encoding="utf-8")
        def runner(worktree: Path, request: dict[str, object]) -> dict[str, object]:
            self.assertEqual((worktree / "docs/note.txt").read_text(), "stable\n")
            (worktree / "src/kernel.cu").write_text("// real-path candidate\n", encoding="utf-8")
            return {"format": "LOCAL-WORKER-REVIEW/1", "verdict": "pass"}
        request = self.request("writable")
        request.update(
            format="CORE4-INTEGRATION-REQUEST/2", schema_version=2,
            read_dependencies=["docs"], approved_overlays=[], execution={"backend": "real"},
        )
        request.pop("fake_changes")
        result = self.controller(writable_runner=runner).run(request)
        self.assertEqual((result["status"], result["child_state"]), ("accepted", "accepted"))
        artifact_root = Path(result["artifact_root"])
        self.assertTrue((artifact_root / "reviewer-evidence.json").is_file())
        self.assertTrue((artifact_root / "acceptance-verification.json").is_file())
        self.assertEqual((self.root / "docs/note.txt").read_text(), "unrelated user work\n")


if __name__ == "__main__":
    unittest.main()
