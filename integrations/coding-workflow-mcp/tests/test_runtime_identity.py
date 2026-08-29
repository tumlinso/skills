from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


PACKAGE = Path(__file__).resolve().parents[1]
SKILLS = PACKAGE.parents[1]


def _runtime(root: Path, marker: str) -> None:
    package = root / "todo-orchestrator/todo_orchestrator"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text(f"MARKER = {marker!r}\n", encoding="utf-8")


def _run(source: str, *, root: Path, extra_pythonpath: Path | None = None) -> subprocess.CompletedProcess[str]:
    pythonpath = [str(PACKAGE)]
    if extra_pythonpath is not None:
        pythonpath.append(str(extra_pythonpath / "todo-orchestrator"))
    environment = dict(os.environ)
    environment["CODING_WORKFLOW_SKILLS_ROOT"] = str(root)
    environment["PYTHONPATH"] = os.pathsep.join(pythonpath)
    environment.pop("CODING_WORKFLOW_RUNTIME_FINGERPRINT", None)
    return subprocess.run([sys.executable, "-c", source], env=environment, text=True,
                          capture_output=True, check=False)


class RuntimeIdentityTests(unittest.TestCase):
    def test_canonical_runtime_wins_over_earlier_pythonpath_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            canonical, alternate = base / "canonical", base / "alternate"
            _runtime(canonical, "canonical")
            _runtime(alternate, "alternate")
            result = _run(
                "from coding_workflow_mcp.runtime_identity import bind_canonical_runtime; "
                "i=bind_canonical_runtime(); import todo_orchestrator; "
                "print(todo_orchestrator.MARKER, i.package_root)",
                root=canonical, extra_pythonpath=alternate,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("canonical", result.stdout)

    def test_preimported_noncanonical_module_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            canonical, alternate = base / "canonical", base / "alternate"
            _runtime(canonical, "canonical")
            _runtime(alternate, "alternate")
            result = _run(
                "import todo_orchestrator; "
                "from coding_workflow_mcp.runtime_identity import bind_canonical_runtime; "
                "bind_canonical_runtime()",
                root=canonical, extra_pythonpath=alternate,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-canonical runtime", result.stderr)

    def test_persistent_process_rejects_runtime_root_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            first, second = base / "a", base / "b"
            _runtime(first, "a")
            _runtime(second, "b")
            result = _run(
                "import os; from coding_workflow_mcp.runtime_identity import bind_canonical_runtime; "
                "bind_canonical_runtime(); os.environ['CODING_WORKFLOW_SKILLS_ROOT']=" + repr(str(second)) + "; "
                "bind_canonical_runtime()",
                root=first,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("non-canonical runtime", result.stderr)

    def test_runtime_fingerprint_change_requires_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "runtime"
            _runtime(root, "a")
            package_file = root / "todo-orchestrator/todo_orchestrator/extra.py"
            result = _run(
                "from pathlib import Path; from coding_workflow_mcp.runtime_identity import "
                "bind_canonical_runtime,validate_runtime; i=bind_canonical_runtime(); "
                f"Path({str(package_file)!r}).write_text('changed\\n'); validate_runtime(i)",
                root=root,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runtime identity changed", result.stderr)

    def test_project_context_reports_canonical_authority_path(self) -> None:
        environment = dict(os.environ)
        environment["CODING_WORKFLOW_SKILLS_ROOT"] = str(SKILLS)
        code = (
            "import json,sys,tempfile; from pathlib import Path; "
            "from coding_workflow_mcp.runtime_identity import bind_canonical_runtime,project_runtime_context; "
            "i=bind_canonical_runtime(); from todo_orchestrator.service import Service; "
            "d=tempfile.TemporaryDirectory(); p=Path(d.name); "
            "s=Service(p,bootstrap=True); c=project_runtime_context(p,i); "
            "print(json.dumps({'context':c,'db':str(s.paths.db_file.resolve()),'uuid':s.project['project_uuid']}))"
        )
        result = subprocess.run([sys.executable, "-c", code], env={**environment, "PYTHONPATH": str(PACKAGE)},
                                text=True, capture_output=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value["context"]["db_path"], value["db"])
        self.assertEqual(value["context"]["project_uuid"], value["uuid"])

    def test_two_persistent_processes_share_runtime_and_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            repo, state = base / "project", base / "state"
            repo.mkdir()
            environment = dict(os.environ)
            environment.update({
                "CODING_WORKFLOW_SKILLS_ROOT": str(SKILLS),
                "TODO_ORCHESTRATOR_STATE_DIR": str(state),
                "PYTHONPATH": str(PACKAGE),
            })
            initialize = (
                "from pathlib import Path; from coding_workflow_mcp.runtime_identity import bind_canonical_runtime; "
                "bind_canonical_runtime(); from todo_orchestrator.service import Service; "
                f"Service.bootstrap(Path({str(repo)!r}), 'concurrent-runtime-test')"
            )
            seeded = subprocess.run([sys.executable, "-c", initialize], env=environment,
                                    text=True, capture_output=True, check=False)
            self.assertEqual(seeded.returncode, 0, seeded.stderr)
            worker = (
                "import json,time; from pathlib import Path; "
                "from coding_workflow_mcp.runtime_identity import bind_canonical_runtime,project_runtime_context; "
                "i=bind_canonical_runtime(); from todo_orchestrator.service import Service; "
                "from todo_orchestrator.semantic import SemanticReader; "
                f"p=Path({str(repo)!r}); c=project_runtime_context(p,i); "
                "\nfor _ in range(8):\n"
                " s=Service(p); r=SemanticReader(p); values=(s.status()['project_revision'],s.export()['project_revision'],r.state()['revision'],r.workflow()['revision']); assert len(set(values)) == 1; time.sleep(.02)\n"
                "print(json.dumps(c,sort_keys=True))"
            )
            readers_env = {**environment, "TODO_ORCHESTRATOR_READ_ONLY": "1"}
            processes = [subprocess.Popen([sys.executable, "-c", worker], env=readers_env,
                                          text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                         for _ in range(2)]
            outputs = [process.communicate(timeout=10) for process in processes]
            for process, (_stdout, stderr) in zip(processes, outputs):
                self.assertEqual(process.returncode, 0, stderr)
            contexts = [json.loads(stdout) for stdout, _stderr in outputs]
            self.assertEqual(contexts[0], contexts[1])
            self.assertEqual(contexts[0]["db_path"], str(next(state.iterdir()) / "state.sqlite3"))


if __name__ == "__main__":
    unittest.main()
