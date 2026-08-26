from __future__ import annotations

import asyncio
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import BackendError, CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore, InvalidHandle
from coding_workflow_mcp.server import SERVER_INSTRUCTIONS, create_server


class FakeBackend(CodingWorkflowBackend):
    def __init__(self, root: Path, store: CapabilityStore) -> None:
        self.root = root.resolve()
        self.store = store
        self.instance_id = "fi_fake"
        self.worker_status = "delegated"
        self.collect_status = "running"
        self.finish_ok = True
        self.gate_status = "pending"
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
                "gates": [{"id": "G-1", "type": "command", "required": 1,
                           "status": self.gate_status, "valid": self.gate_status == "passed"}],
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
                "gates": [{"id": "G-1", "type": "command", "required": 1,
                           "status": self.gate_status, "valid": self.gate_status == "passed"}],
            }}
        if arguments[:3] == ("gate", "run", "--required"):
            self.gate_status = "passed"
            return {"ok": True, "data": {"results": [
                {"gate_id": "G-1", "status": "passed", "valid": True, "project_revision": 13}
            ]}}
        if arguments[:2] == ("recover", "terminal-checkpoints"):
            return {"ok": True, "data": {
                "status": "finalized", "task_id": arguments[2],
                "checkpoint_id": None, "reached": [{"checkpoint_id": "C-1"}],
                "already_reached": [], "rejected": [],
                "completion_revision": 13, "project_revision": 14,
                "idempotent_noop": False,
            }}
        if command in {"complete", "handoff", "block", "release"}:
            if self.finish_ok:
                return {"ok": True, "data": {"project_revision": 14}}
            return {"ok": False, "code": "required_gates_unsatisfied",
                    "error": {"details": []}}
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


class RestartAuthorityBackend(FakeBackend):
    def __init__(self, root: Path, store: CapabilityStore, authority: dict) -> None:
        super().__init__(root, store)
        self.authority = authority

    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False):
        self.calls.append(tuple(arguments))
        command = arguments[0]
        if command == "bootstrap":
            return {"ok": True, "data": {
                "project_uuid": "project-restart", "project_revision": self.authority["revision"]
            }}
        if command == "continue":
            self.authority["continue_calls"] += 1
            if self.authority["active"]:
                return {"ok": False, "code": "no_actionable_work",
                        "data": {"message": "No safe task is currently claimable"}}
            self.authority["active"] = True
            self.authority["revision"] = 11
            return {"ok": True, "data": {
                "project_revision": 11,
                "claim": {"claim_token": "toc_restart_secret"},
                "session": {"session_token": "tos_restart_secret"},
                "task": {"id": "CE-ARCH-71", "title": "Resume", "objective": "Bounded recovery",
                         "next_action": "finish through facade"},
                "scope": {"exclusive_paths": ["src"], "read_paths": ["include"],
                          "forbidden_paths": []},
                "interlocks": [{"rule": "Preserve active claim authority."}],
                "gates": [{"id": "G-1", "type": "command", "required": 1,
                           "status": "passed", "valid": True}],
            }}
        token = arguments[arguments.index("--claim-token") + 1] if "--claim-token" in arguments else None
        if token != "toc_restart_secret" or not self.authority["active"]:
            return {"ok": False, "code": "invalid_claim"}
        if command == "pulse":
            self.authority["revision"] += 1
            return {"ok": True, "data": {"project_revision": self.authority["revision"]}}
        if command == "context":
            return {"ok": True, "data": {
                "project_revision": self.authority["revision"],
                "task": {"id": "CE-ARCH-71", "title": "Resume", "objective": "Bounded recovery",
                         "next_action": "finish through facade"},
                "scope": {"exclusive_paths": ["src"], "read_paths": ["include"],
                          "forbidden_paths": []},
                "interlocks": [{"rule": "Preserve active claim authority."}],
                "gates": [{"id": "G-1", "type": "command", "required": 1,
                           "status": "passed", "valid": True}],
            }}
        if command == "complete":
            self.authority["complete_calls"] += 1
            self.authority["active"] = False
            self.authority["revision"] += 1
            return {"ok": True, "data": {"project_revision": self.authority["revision"]}}
        raise AssertionError(arguments)


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
        continued = next(call for call in self.backend.calls if call and call[0] == "continue")
        self.assertEqual(continued[continued.index("--owner-system") + 1], "coding-workflow")
        self.assertTrue(continued[continued.index("--owner-instance") + 1].startswith("fi_"))

    def test_explicit_task_recovers_claim_after_facade_restart(self) -> None:
        authority = {"active": False, "revision": 10, "continue_calls": 0, "complete_calls": 0}
        first = RestartAuthorityBackend(self.root, self.store, authority)
        claimed = first.next_task(str(self.root), "CE-ARCH-71")
        original = claimed["workflow_handle"]

        restarted_store = CapabilityStore(self.root / "state")
        restarted = RestartAuthorityBackend(self.root, restarted_store, authority)
        resumed = restarted.next_task(str(self.root), "CE-ARCH-71")
        encoded = json.dumps(resumed, ensure_ascii=False).encode()

        self.assertEqual(resumed["status"], "claimed")
        self.assertTrue(resumed["resumed"])
        self.assertNotEqual(resumed["workflow_handle"], original)
        self.assertEqual(resumed["task"]["id"], "CE-ARCH-71")
        self.assertEqual(resumed["revision"], 12)
        self.assertEqual(authority["continue_calls"], 1)
        self.assertNotIn(b"toc_restart_secret", encoded)
        self.assertNotIn(b"tos_restart_secret", encoded)
        self.assertEqual(
            restarted_store.get_workflow(original)["claim_token"],
            restarted_store.get_workflow(resumed["workflow_handle"])["claim_token"],
        )

        finished = restarted.finish_task(
            resumed["workflow_handle"], "complete", "implemented", "recovered", None
        )
        self.assertEqual(finished["status"], "finished")
        self.assertEqual(finished["revision"], 14)
        self.assertEqual(authority["continue_calls"], 1)
        self.assertEqual(authority["complete_calls"], 1)
        self.assertFalse(authority["active"])
        with self.assertRaises(InvalidHandle):
            restarted_store.get_workflow(resumed["workflow_handle"])
        with self.assertRaises(InvalidHandle):
            restarted_store.get_workflow(original)

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

    def test_source_inspection_recovers_missing_index_for_proven_path(self) -> None:
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        (self.root / "src").mkdir()
        (self.root / "src/widget.cc").write_text("int widget() { return 1; }\n", encoding="utf-8")
        (self.root / ".ctxpp.toml").write_text("version = 1\n", encoding="utf-8")

        class RecoveringBackend(FakeBackend):
            def __init__(inner_self, root, store):
                super().__init__(root, store)
                inner_self.indexed = False

            def ctxpp(inner_self, repo, *arguments, timeout=30):
                inner_self.calls.append(("ctxpp", *arguments))
                command = arguments[0]
                if command == "init":
                    return {"format": "CTXPP-INIT/1", "ok": True}
                if command == "scan":
                    inner_self.indexed = True
                    return {"format": "CTXPP-SCAN/1", "backend": "semantic"}
                if not inner_self.indexed:
                    raise BackendError("invalid_public_cli_envelope")
                return {"target": {"name": "widget"},
                        "edit_locations": [{"path": "src/widget.cc", "line": 1}],
                        "trust": {"relationships": "semantic"}, "content": "bounded"}

        backend = RecoveringBackend(self.root, self.store)
        handle = backend.next_task(str(self.root))["workflow_handle"]
        result = backend.inspect_task(handle, "source", "src/widget.cc", "understand", 2400)
        self.assertEqual(result["status"], "available")
        operations = [call[1] for call in backend.calls if call and call[0] == "ctxpp"]
        self.assertEqual(operations.count("init"), 1)
        self.assertEqual(operations.count("scan"), 1)

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
        ce_objective = (
            "CE-ARCH-71 bounded implementation seam only: inspect prepared operation registration."
        )
        delegated = self.backend.delegate_task(workflow, "auto", ce_objective)
        self.assertEqual(delegated["status"], "delegated")
        self.assertEqual(delegated["mode"], "readonly")
        worker_call = next(call for call in reversed(self.backend.calls) if call and call[:2] == ("worker", "delegate"))
        self.assertIn("--objective", worker_call)
        self.assertEqual(worker_call[worker_call.index("--objective") + 1], ce_objective)
        self.assertNotIn("--target", worker_call)
        running = self.backend.collect_delegation(delegated["delegation_handle"])
        self.assertEqual(running, {"status": "running", "instruction": "continue_frontier_or_collect_later",
                                   "poll_recommended": False})
        self.backend.collect_status = "accepted"
        accepted = self.backend.collect_delegation(delegated["delegation_handle"])
        self.assertEqual(accepted["status"], "accepted")
        self.assertFalse(accepted["parent_task_completed"])
        second = self.backend.delegate_task(workflow, "readonly", None)
        self.backend.collect_status = "no_change"
        self.assertEqual(self.backend.collect_delegation(second["delegation_handle"])["status"], "completed")

    def test_finish_executes_one_disposition_and_invalidates_handle(self) -> None:
        handle = self.claim()["workflow_handle"]
        result = self.backend.finish_task(handle, "complete", "implemented", "bounded", None)
        self.assertEqual(result["status"], "finished")
        self.assertEqual(result["gates"], [{"id": "G-1", "status": "passed", "valid": True}])
        with self.assertRaises(InvalidHandle):
            self.store.get_workflow(handle)
        dispositions = [call for call in self.backend.calls if call and call[0] in {"complete", "handoff", "block", "release"}]
        self.assertEqual(len(dispositions), 1)
        blocked_handle = self.claim()["workflow_handle"]
        self.backend.finish_ok = False
        blocked = self.backend.finish_task(blocked_handle, "complete", "validated", None, None)
        self.assertEqual(blocked, {
            "status": "internal_consistency_error",
            "reason": "completion_gate_error_contradicts_authoritative_gate_state",
        })
        self.assertEqual(self.store.get_workflow(blocked_handle)["task_id"], "T-1")

    def test_release_preserves_todo_lifecycle_vocabulary(self) -> None:
        handle = self.claim()["workflow_handle"]
        result = self.backend.finish_task(handle, "release", "failed", None, "retry later")
        self.assertEqual(result["status"], "finished")
        release = next(call for call in self.backend.calls if call and call[0] == "release")
        self.assertNotIn("--status", release)
        self.assertIn("--reason", release)

    def test_invalid_handle_is_compact_structured_error(self) -> None:
        server = create_server(self.backend)
        result = asyncio.run(server._tool_manager.call_tool(
            "inspect_task", {"workflow_handle": "wf_missing", "focus": "task"}
        ))
        self.assertEqual(result["status"], "invalid_handle")

    def test_exact_seven_tools_annotations_and_schema_budget(self) -> None:
        server = create_server(self.backend)
        tools = asyncio.run(server.list_tools())
        self.assertEqual({tool.name for tool in tools}, {
            "next_task", "inspect_task", "delegate_task", "collect_delegation", "run_gates",
            "recover_terminal_checkpoints", "finish_task"
        })
        by_name = {tool.name: tool for tool in tools}
        expected_readonly = {"next_task": False, "inspect_task": True, "delegate_task": False,
                             "collect_delegation": True, "run_gates": False,
                             "recover_terminal_checkpoints": False, "finish_task": False}
        for name, readonly in expected_readonly.items():
            annotations = by_name[name].annotations
            self.assertEqual(annotations.readOnlyHint, readonly)
            self.assertFalse(annotations.destructiveHint)
            self.assertEqual(annotations.idempotentHint, readonly or name == "recover_terminal_checkpoints")
        serialized = json.dumps([tool.model_dump(mode="json") for tool in tools], separators=(",", ":"))
        self.assertLess(len(serialized.encode()), 14_000)
        self.assertLess(len(SERVER_INSTRUCTIONS), 1_200)
        self.assertIn("Call next_task once", SERVER_INSTRUCTIONS[:512])

    def test_shell_string_is_rejected(self) -> None:
        with self.assertRaises(TypeError):
            self.backend._run_json("echo unsafe", cwd=self.root)


if __name__ == "__main__":
    unittest.main()
