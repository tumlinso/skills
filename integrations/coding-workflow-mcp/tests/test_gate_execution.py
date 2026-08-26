from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore
from test_tools import FakeBackend


FORBIDDEN_RESPONSE_TEXT = (
    "toc_", "tos_", "claim_token", "session_token",
    "toc_claim_secret", "tos_session_secret",
)


class GateBackend(FakeBackend):
    def __init__(self, root: Path, store: CapabilityStore) -> None:
        super().__init__(root, store)
        self.gate_ids = ["G-1"]
        self.fail_gate_ids: set[str] = set()
        self.keep_pending_after_run = False
        self.no_required_gates = False

    def _gate_rows(self) -> list[dict[str, object]]:
        if self.no_required_gates:
            return []
        return [
            {
                "id": gate_id,
                "type": "command",
                "required": 1,
                "status": "failed" if gate_id in self.fail_gate_ids else self.gate_status,
                "valid": gate_id not in self.fail_gate_ids and self.gate_status == "passed",
            }
            for gate_id in self.gate_ids
        ]

    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False):
        if arguments and arguments[0] == "continue":
            result = super().todo(repo, *arguments, allow_failure=allow_failure)
            result["data"]["gates"] = self._gate_rows()
            return result
        if arguments and arguments[0] == "context" and "--section" not in arguments:
            self.calls.append(tuple(arguments))
            return {"ok": True, "data": {
                "project_revision": 20,
                "task": {"id": "T-1", "title": "Implement", "objective": "Bounded", "next_action": "test"},
                "scope": {"exclusive_paths": ["src"], "read_paths": [], "forbidden_paths": []},
                "gates": self._gate_rows(),
            }}
        if arguments[:3] == ("gate", "run", "--required"):
            self.calls.append(tuple(arguments))
            results = [
                {
                    "gate_id": gate_id,
                    "status": "failed" if gate_id in self.fail_gate_ids else "passed",
                    "valid": gate_id not in self.fail_gate_ids,
                    "project_revision": 21 + index,
                }
                for index, gate_id in enumerate(self.gate_ids)
            ]
            if not self.keep_pending_after_run:
                self.gate_status = "passed"
            if self.fail_gate_ids:
                return {"ok": False, "code": "gate_failed", "error": {
                    "message": "secret-free public failure",
                    "details": {"results": results, "failed": [
                        item for item in results if not item["valid"]
                    ]},
                }}
            return {"ok": True, "data": {"results": results}}
        return super().todo(repo, *arguments, allow_failure=allow_failure)


class EmptyGateRegressionBackend(GateBackend):
    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False):
        if arguments and arguments[0] == "complete":
            self.calls.append(tuple(arguments))
            return {"ok": False, "code": "required_gates_unsatisfied", "error": {
                "message": "Required gates are missing", "details": [],
            }}
        return super().todo(repo, *arguments, allow_failure=allow_failure)


class GateExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.store = CapabilityStore(self.root / "state")
        self.backend = GateBackend(self.root, self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _claim(self) -> str:
        return str(self.backend.next_task(str(self.root))["workflow_handle"])

    def assert_response_is_secret_free(self, response: dict[str, object]) -> None:
        encoded = json.dumps(response, sort_keys=True)
        for forbidden in FORBIDDEN_RESPONSE_TEXT:
            self.assertNotIn(forbidden, encoded)

    def test_required_gate_auto_runs_and_completion_is_secret_free(self) -> None:
        handle = self._claim()
        result = self.backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["gates"], [{"id": "G-1", "status": "passed", "valid": True}])
        self.assert_response_is_secret_free(result)
        self.assertEqual(len([call for call in self.backend.calls if call[:3] == ("gate", "run", "--required")]), 1)

    def test_required_gate_failure_leaves_workflow_usable(self) -> None:
        self.backend.fail_gate_ids = {"G-1"}
        handle = self._claim()
        result = self.backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(result["status"], "gate_failed")
        self.assertEqual(result["failed_gate_ids"], ["G-1"])
        self.assertEqual(result["gates"], [{"id": "G-1", "status": "failed", "valid": False}])
        self.assertEqual(self.backend.inspect_task(handle, "task", None, "test", 2400)["status"], "current")
        self.assert_response_is_secret_free(result)
        self.assertFalse(any(call and call[0] == "complete" for call in self.backend.calls))

    def test_explicit_run_then_complete_skips_reexecution(self) -> None:
        handle = self._claim()
        gates = self.backend.run_gates(handle)
        self.assertEqual(gates["status"], "passed")
        self.assertEqual(gates["revision"], 21)
        self.assertEqual(self.store.get_workflow(handle)["revision"], 21)
        finished = self.backend.finish_task(handle, "complete", "validated", None, None)
        self.assertEqual(finished["status"], "finished")
        self.assertEqual(len([call for call in self.backend.calls if call[:3] == ("gate", "run", "--required")]), 1)
        self.assert_response_is_secret_free(gates)
        self.assert_response_is_secret_free(finished)

    def test_multiple_required_gates_are_all_reported(self) -> None:
        self.backend.gate_ids = ["G-A", "G-B", "G-C"]
        handle = self._claim()
        result = self.backend.run_gates(handle)
        self.assertEqual(result["status"], "passed")
        self.assertEqual([item["id"] for item in result["gates"]], ["G-A", "G-B", "G-C"])
        self.assertTrue(all(item["valid"] for item in result["gates"]))
        self.assertEqual(result["revision"], 23)

    def test_no_required_gates_completes_without_gate_invocation(self) -> None:
        self.backend.no_required_gates = True
        handle = self._claim()
        result = self.backend.finish_task(handle, "complete", "no_change_required", None, None)
        self.assertEqual(result["status"], "finished")
        self.assertFalse(any(call[:3] == ("gate", "run", "--required") for call in self.backend.calls))

    def test_non_complete_actions_do_not_run_gates(self) -> None:
        for action, reason in (("release", "retry"), ("handoff", "continue elsewhere"), ("block", "blocked")):
            with self.subTest(action=action):
                backend = GateBackend(self.root, CapabilityStore(self.root / f"state-{action}"))
                handle = str(backend.next_task(str(self.root))["workflow_handle"])
                result = backend.finish_task(handle, action, "failed", None, reason)
                self.assertEqual(result["status"], "finished")
                self.assertFalse(any(call[:3] == ("gate", "run", "--required") for call in backend.calls))

    def test_empty_gate_required_regression_uses_authoritative_pending_ids(self) -> None:
        backend = EmptyGateRegressionBackend(self.root, CapabilityStore(self.root / "state-regression"))
        backend.keep_pending_after_run = True
        handle = str(backend.next_task(str(self.root))["workflow_handle"])
        result = backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(result["status"], "gate_required")
        self.assertEqual(result["missing_gate_ids"], ["G-1"])
        self.assertTrue(result["gates"])
        self.assert_response_is_secret_free(result)


class RealGateExecutionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "src").mkdir()
        (self.root / "src/value.py").write_text("VALUE = 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.email", "gate-test@example.invalid"], cwd=self.root, check=True)
        subprocess.run(["git", "config", "user.name", "Gate Test"], cwd=self.root, check=True)
        subprocess.run(["git", "add", "src/value.py"], cwd=self.root, check=True)
        subprocess.run(["git", "commit", "-qm", "fixture"], cwd=self.root, check=True)
        skills_root = Path(__file__).resolve().parents[3]
        self.backend = CodingWorkflowBackend(
            CapabilityStore(self.root / "capabilities"), skills_root=skills_root
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _claim(self, gates: list[dict[str, object]]) -> str:
        plan = {
            "schema_version": 2,
            "project": {"name": "Facade Gate Integration"},
            "tasks": [{
                "id": "GATE-TASK",
                "kind": "workstream",
                "title": "Exercise facade gates",
                "objective": "Exercise required gate execution through the opaque facade.",
                "priority": 100,
                "parallel_policy": "serial",
                "scope": {"exclusive_paths": ["src/value.py"]},
                "gates": gates,
            }],
        }
        plan_path = self.root / ".git" / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        self.backend.todo(self.root, "bootstrap", "--name", "Facade Gate Integration")
        self.backend.todo(self.root, "plan", "validate", "--file", str(plan_path))
        self.backend.todo(self.root, "plan", "apply", "--file", str(plan_path))
        return str(self.backend.next_task(str(self.root), "GATE-TASK")["workflow_handle"])

    def test_real_todo_required_gate_runs_before_completion(self) -> None:
        handle = self._claim([{
            "id": "PASS", "type": "command",
            "argv": [sys.executable, "-c", "raise SystemExit(0)"], "required": True,
        }])
        result = self.backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["gates"], [{"id": "PASS", "status": "passed", "valid": True}])
        encoded = json.dumps(result, sort_keys=True)
        for forbidden in FORBIDDEN_RESPONSE_TEXT:
            self.assertNotIn(forbidden, encoded)

    def test_real_todo_required_gate_failure_preserves_claim(self) -> None:
        handle = self._claim([{
            "id": "FAIL", "type": "command",
            "argv": [sys.executable, "-c", "raise SystemExit(7)"], "required": True,
        }])
        result = self.backend.finish_task(handle, "complete", "implemented", None, None)
        self.assertEqual(result["status"], "gate_failed")
        self.assertEqual(result["failed_gate_ids"], ["FAIL"])
        self.assertEqual(self.backend.inspect_task(handle, "task", None, "test", 2400)["status"], "current")


if __name__ == "__main__":
    unittest.main()
