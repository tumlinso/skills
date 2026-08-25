from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parent
WORKER = SKILL / "scripts/local_worker.py"
CTXPP = REPO / "cpp-context-compiler/scripts/ctxpp"
FIXTURE = REPO / "cpp-context-compiler/tests/fixtures/sample"


class ReadOnlyMvpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        subprocess.run([str(REPO / "cpp-context-compiler/scripts/build_tool.sh")], cwd=REPO / "cpp-context-compiler",
                       check=True, text=True, capture_output=True)
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / "repo"
        shutil.copytree(FIXTURE, cls.root, ignore=shutil.ignore_patterns("build", ".ctxpp", "__pycache__"))
        subprocess.run(["git", "init", "-q"], cwd=cls.root, check=True)
        os.chmod(cls.root / "tests/tokenizer.py", 0o755)
        subprocess.run(["cmake", "-S", ".", "-B", "build", "-DCMAKE_BUILD_TYPE=Release"], cwd=cls.root,
                       check=True, text=True, capture_output=True)
        subprocess.run(["cmake", "--build", "build", "--parallel", "2"], cwd=cls.root,
                       check=True, text=True, capture_output=True)
        subprocess.run([str(CTXPP), "--root", str(cls.root), "--json", "scan"], cwd=cls.root,
                       check=True, text=True, capture_output=True)
        cls.todo_log = Path(cls.temp.name) / "todo-log.jsonl"
        cls.fake_todo = Path(cls.temp.name) / "fake_todo.py"
        cls.fake_todo.write_text(
            "#!/usr/bin/env python3\n"
            "import json,os,sys\n"
            "with open(os.environ['LCW_TODO_LOG'],'a') as f: f.write(json.dumps(sys.argv[1:])+'\\n')\n"
            "print(json.dumps({'ok':True,'data':{'state':'running'}}))\n",
            encoding="utf-8",
        )
        cls.fake_ctxpp = Path(cls.temp.name) / "fake_ctxpp.py"
        cls.fake_ctxpp.write_text(
            "#!/usr/bin/env python3\n"
            "import hashlib,json,sys\n"
            "from pathlib import Path\n"
            "root=Path(sys.argv[sys.argv.index('--root')+1]); source=root/'src/plan.cpp'; data=source.read_bytes()\n"
            "packet={'format':'CTXPP-CONTEXT-PACKET/1','readonly':True,'target':{'name':'demo::PackingPlan::freeze','location':{'path':'src/plan.cpp','line':1,'end_line':1,'content_sha256':hashlib.sha256(data).hexdigest()}},'trust':{'target_range':'hash-verified','relationships':'semantic','index_incomplete':False},'coverage':{'sufficient':True},'packet_hash':'1'*64,'source_identity':{'schema_version':1,'repo_root':str(root),'git_head':None,'dirty_paths':[],'fingerprint':'2'*64},'estimated_tokens':100}\n"
            "print(json.dumps(packet))\n",
            encoding="utf-8",
        )
        os.chmod(cls.fake_ctxpp, 0o755)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def setUp(self) -> None:
        self.todo_log.write_text("", encoding="utf-8")

    def request(self, **updates) -> dict:
        value = {
            "format": "LCW-REQUEST/1",
            "schema_version": 1,
            "backend": "fake",
            "role": "explain",
            "readonly": True,
            "repo_root": str(self.root),
            "child_token": "toch_test_restricted_token",
            "objective": "Explain the freeze invariant without changing source.",
            "scopes": ["src/plan.cpp", "include/plan.hpp"],
            "target": "demo::PackingPlan::freeze",
            "intent": "understand",
            "budget_tokens": 10000,
            "max_items": 32,
        }
        value.update(updates)
        return value

    def invoke(self, command: str, request: dict, *, fake_ctxpp: bool = False) -> subprocess.CompletedProcess[str]:
        request_path = Path(self.temp.name) / f"request-{command}.json"
        request_path.write_text(json.dumps(request), encoding="utf-8")
        env = dict(os.environ)
        env.update({"LCW_TODO_CLI": str(self.fake_todo), "LCW_TODO_LOG": str(self.todo_log)})
        if fake_ctxpp:
            env["LCW_CTXPP_CLI"] = str(self.fake_ctxpp)
        return subprocess.run(["python", str(WORKER), command, "--request", str(request_path)], cwd=SKILL,
                              text=True, capture_output=True, env=env)

    def test_eligibility_is_deterministic_and_rejects_writable_or_recursive_requests(self) -> None:
        delegation = json.loads((SKILL / "schemas/delegation-spec-v1.schema.json").read_text(encoding="utf-8"))
        result = json.loads((SKILL / "schemas/worker-result-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(delegation["properties"]["readonly"]["const"], True)
        self.assertEqual(result["properties"]["changed_paths"]["const"], [])
        writable = self.invoke("eligible", self.request(readonly=False))
        self.assertEqual(writable.returncode, 2)
        self.assertFalse(json.loads(writable.stdout)["eligible"])
        recursive = self.invoke("eligible", {**self.request(), "recursive_agents": True})
        self.assertEqual(recursive.returncode, 2)
        self.assertIn("extra=['recursive_agents']", json.loads(recursive.stdout)["reasons"][0])

    def test_fake_backend_uses_child_authorization_and_preserves_canonical_source(self) -> None:
        source = self.root / "src/plan.cpp"
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        process = self.invoke("run", self.request())
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        result = json.loads(process.stdout)
        self.assertEqual(result["format"], "LOCAL-CODING-WORKER-RESULT/1")
        self.assertEqual(result["status"], "needs_codex")
        self.assertEqual(result["changed_paths"], [])
        self.assertTrue(result["child_reported"])
        self.assertEqual(result["telemetry"]["backend_calls"], 1)
        self.assertEqual(result["telemetry"]["tool_calls"], 3)
        self.assertGreater(result["telemetry"]["snapshot_paths"], 2)
        self.assertNotIn("toch_", process.stdout)
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(), before)
        calls = [json.loads(line) for line in self.todo_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual([call[1] for call in calls], ["heartbeat", "report"])
        self.assertIn("needs_codex", calls[1])

    def test_target_outside_scope_escalates_without_writes(self) -> None:
        process = self.invoke("run", self.request(scopes=["include/plan.hpp"]))
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "needs_codex")
        self.assertIn("outside", result["summary"])
        self.assertEqual(result["changed_paths"], [])

    def test_complete_fake_packet_normalizes_success_to_no_change(self) -> None:
        process = self.invoke("run", self.request(), fake_ctxpp=True)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "no_change")
        self.assertIn("hash-verified", result["summary"])
        self.assertEqual(result["changed_paths"], [])
        calls = [json.loads(line) for line in self.todo_log.read_text(encoding="utf-8").splitlines()]
        self.assertIn("succeeded", calls[1])

    def test_v2_long_objective_uses_task_spec_file_without_path_length_failure(self) -> None:
        request = self.request(
            format="LCW-REQUEST/2", schema_version=2,
            objective="Review the bounded CE operation seam. " + ("constraint " * 40),
            execution={"backend": "fake", "harness": "qwen", "gpu_count": 1},
        )
        process = self.invoke("run", request, fake_ctxpp=True)
        self.assertEqual(process.returncode, 0, process.stderr + process.stdout)
        self.assertEqual(json.loads(process.stdout)["status"], "no_change")


if __name__ == "__main__":
    unittest.main()
