from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore, InvalidHandle
from coding_workflow_mcp.server import SERVER_INSTRUCTIONS, create_server


class FakeBackend(CodingWorkflowBackend):
    def __init__(self, root: Path, store: CapabilityStore) -> None:
        self.root = root.resolve()
        self.store = store
        self.worker_status = "delegated"
        self.collect_status = "running"
        self.finish_ok = True
        self.calls: list[tuple[str, ...]] = []

    def canonical_repo(self, repo_root: str) -> Path:
        return self.root

    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False):
        self.calls.append(tuple(arguments))
        command = arguments[0]
        if command == "bootstrap":
            return {"ok": True, "data": {"project_uuid": "project-1", "project_revision": 10}}
        if command == "continue":
            return {"ok": True, "data": {
                "project_revision": 11,
                "claim": {"claim_token": "toc_claim_secret"},
                "session": {"session_token": "tos_session_secret"},
                "task": {"id": "T-1", "title": "Implement", "objective": "Bounded objective", "next_action": "edit"},
                "scope": {"exclusive_paths": ["src"], "read_paths": ["include"], "forbidden_paths": ["vendor"]},
                "interlocks": [{"rule": "Preserve the public interface."}],
                "gates": [{"id": "G-1", "type": "command", "required": 1, "status": "pending"}],
            }}
        if command == "pulse":
            return {"ok": True, "data": {"project_revision": 12}}
        if command == "context":
            if "--section" in arguments:
                return {"ok": True, "data": {"events": [{"kind": "gate", "summary": "passed"}]}}
            return {"ok": True, "data": {
                "project_revision": 12,
                "task": {"id": "T-1", "title": "Implement", "objective": "Bounded objective", "next_action": "test"},
                "scope": {"exclusive_paths": ["src"], "read_paths": ["include"], "forbidden_paths": []},
                "gates": [{"id": "G-1", "type": "command", "required": 1, "status": "passed"}],
            }}
        if command in {"complete", "handoff", "block", "release"}:
            if self.finish_ok:
                return {"ok": True, "data": {"project_revision": 13}}
            return {"ok": False, "code": "gate_required", "data": {"missing_gate_ids": ["G-1"]}}
        raise AssertionError(arguments)

    def ctxpp(self, repo: Path, *arguments: str):
        self.calls.append(("ctxpp", *arguments))
        return {"target": "Widget", "edit_locations": [{"path": "src/widget.cc", "line": 7}],
                "trust": {"target_range": "hash-verified"}, "tests": ["widget_test"],
                "content": "safe toc_hidden_value"}

    def worker(self, repo: Path, *arguments: str, timeout: float = 30):
        self.calls.append(("worker", *arguments))
        if "--collect" in arguments:
            if self.collect_status == "running":
                return {"status": "running"}
            return {"status": self.collect_status, "summary": "done", "changed_paths": ["src/widget.cc"],
                    "verification": [{"id": "G-1", "status": "passed"}], "risk": "low"}
        if self.worker_status == "local_unavailable":
            return {"status": "local_unavailable", "reason": "all_local_worker_slots_busy",
                    "child_created": False, "scope_locked": False}
        if self.worker_status == "unsafe_unavailable":
            return {"status": "local_unavailable", "reason": "busy"}
        if self.worker_status == "not_eligible":
            return {"status": "not_eligible", "reason": "architecture_or_verification_contract_is_not_bounded"}
        return {"status": "delegated", "execution_id": "execution-1", "mode": "readonly"}


class ToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.store = CapabilityStore(self.root / "state")
        self.backend = FakeBackend(self.root, self.store)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def claim(self) -> dict:
        return self.backend.next_task(str(self.root))

    def test_next_task_is_compact_and_secrets_stay_behind_alias(self) -> None:
        result = self.claim()
        encoded = json.dumps(result, ensure_ascii=False).encode()
        self.assertLessEqual(len(encoded), 4_000)
        self.assertEqual(result["status"], "claimed")
        self.assertTrue(result["workflow_handle"].startswith("wf_"))
        self.assertNotIn(b"toc_claim_secret", encoded)
        self.assertNotIn(b"tos_session_secret", encoded)
        stored = self.store.get_workflow(result["workflow_handle"])
        self.assertEqual(stored["claim_token"], "toc_claim_secret")

    def test_inspection_routes_and_redacts_bounded_source(self) -> None:
        handle = self.claim()["workflow_handle"]
        task = self.backend.inspect_task(handle, "task", None, "understand", 2400)
        self.assertEqual(task["status"], "current")
        source = self.backend.inspect_task(handle, "source", "Widget", "edit", 2400)
        self.assertEqual(source["status"], "available")
        encoded = json.dumps(source).encode()
        self.assertLessEqual(len(encoded), 6_000)
        self.assertNotIn(b"toc_hidden_value", encoded)
        evidence = self.backend.inspect_task(handle, "evidence", None, "test", 2400)
        self.assertEqual(evidence["evidence"][0]["summary"], "passed")

    def test_opportunistic_delegation_and_nonblocking_collection(self) -> None:
        workflow = self.claim()["workflow_handle"]
        self.backend.worker_status = "local_unavailable"
        unavailable = self.backend.delegate_task(workflow, "auto", None)
        self.assertEqual(unavailable, {
            "status": "local_unavailable", "reason": "all_local_worker_slots_busy",
            "fallback": "continue_frontier", "retry_recommended": False,
            "child_created": False, "scope_locked": False,
        })
        self.assertLessEqual(len(json.dumps(unavailable).encode()), 700)
        self.backend.worker_status = "unsafe_unavailable"
        unsafe = self.backend.delegate_task(workflow, "writable", None)
        self.assertEqual(unsafe["status"], "attention_required")
        self.backend.worker_status = "delegated"
        delegated = self.backend.delegate_task(workflow, "auto", "Widget")
        self.assertEqual(delegated["status"], "delegated")
        self.assertEqual(delegated["mode"], "readonly")
        running = self.backend.collect_delegation(delegated["delegation_handle"])
        self.assertEqual(running, {"status": "running", "instruction": "continue_frontier_or_collect_later",
                                   "poll_recommended": False})
        self.backend.collect_status = "accepted"
        accepted = self.backend.collect_delegation(delegated["delegation_handle"])
        self.assertEqual(accepted["status"], "accepted")
        self.assertFalse(accepted["parent_task_completed"])

    def test_finish_executes_one_disposition_and_invalidates_handle(self) -> None:
        handle = self.claim()["workflow_handle"]
        result = self.backend.finish_task(handle, "complete", "implemented", "bounded", None)
        self.assertEqual(result["status"], "finished")
        with self.assertRaises(InvalidHandle):
            self.store.get_workflow(handle)
        dispositions = [call for call in self.backend.calls if call and call[0] in {"complete", "handoff", "block", "release"}]
        self.assertEqual(len(dispositions), 1)
        blocked_handle = self.claim()["workflow_handle"]
        self.backend.finish_ok = False
        blocked = self.backend.finish_task(blocked_handle, "complete", "validated", None, None)
        self.assertEqual(blocked, {"status": "gate_required", "missing_gate_ids": ["G-1"]})
        self.assertEqual(self.store.get_workflow(blocked_handle)["task_id"], "T-1")

    def test_invalid_handle_is_compact_structured_error(self) -> None:
        server = create_server(self.backend)
        result = asyncio.run(server._tool_manager.call_tool(
            "inspect_task", {"workflow_handle": "wf_missing", "focus": "task"}
        ))
        self.assertEqual(result["status"], "invalid_handle")

    def test_exact_five_tools_annotations_and_schema_budget(self) -> None:
        server = create_server(self.backend)
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools}, {
            "next_task", "inspect_task", "delegate_task", "collect_delegation", "finish_task"
        })
        by_name = {tool.name: tool for tool in tools}
        expected_readonly = {"next_task": False, "inspect_task": True, "delegate_task": False,
                             "collect_delegation": True, "finish_task": False}
        for name, readonly in expected_readonly.items():
            annotations = by_name[name].annotations
            self.assertEqual(annotations.readOnlyHint, readonly)
            self.assertFalse(annotations.destructiveHint)
            self.assertEqual(annotations.idempotentHint, readonly)
        serialized = json.dumps([tool.model_dump(mode="json") for tool in tools], separators=(",", ":"))
        self.assertLess(len(serialized.encode()), 14_000)
        self.assertLess(len(SERVER_INSTRUCTIONS), 1_200)
        self.assertIn("Call next_task once", SERVER_INSTRUCTIONS[:512])

    def test_shell_string_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.backend._run_json("echo unsafe", cwd=self.root)


if __name__ == "__main__":
    unittest.main()

