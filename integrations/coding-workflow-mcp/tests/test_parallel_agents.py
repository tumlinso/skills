from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coding_workflow_mcp.backend import CodingWorkflowBackend
from coding_workflow_mcp.handles import CapabilityStore
from coding_workflow_mcp.server import create_server


class TwoSlotAdmission:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.available = [0, 1]
        self.executions: dict[str, dict[str, object]] = {}
        self.children_created = 0
        self.scopes_locked = 0
        self.unavailable_calls = 0

    def delegate(self, agent: str, mode: str) -> dict[str, object]:
        with self.lock:
            if not self.available:
                self.unavailable_calls += 1
                return {
                    "status": "local_unavailable",
                    "reason": "all_local_worker_slots_busy",
                    "child_created": False,
                    "scope_locked": False,
                }
            slot = self.available.pop(0)
            execution = f"execution-{agent}-{slot}"
            self.children_created += 1
            self.scopes_locked += 1
            self.executions[execution] = {"slot": slot, "status": "running", "agent": agent}
            return {"status": "delegated", "execution_id": execution,
                    "mode": "readonly" if mode == "auto" else mode}

    def complete(self, execution: str) -> None:
        with self.lock:
            record = self.executions[execution]
            record["status"] = "accepted"
            self.available.append(int(record["slot"]))
            self.available.sort()
            self.scopes_locked -= 1

    def collect(self, execution: str) -> dict[str, object]:
        with self.lock:
            record = self.executions[execution]
            if record["status"] == "running":
                return {"status": "running"}
            return {"status": "accepted", "summary": "bounded result",
                    "changed_paths": [], "verification": [], "risk": "low", "blocker": None}


class ParallelFakeBackend(CodingWorkflowBackend):
    def __init__(self, root: Path, state: Path, agent: str, admission: TwoSlotAdmission) -> None:
        self.root = root.resolve()
        self.store = CapabilityStore(state)
        self.agent = agent
        self.instance_id = f"fi_{agent}"
        self.admission = admission
        self.pulses = 0
        self.blocked_states = 0
        self.delegate_calls = 0

    def canonical_repo(self, repo_root: str) -> Path:
        return self.root

    def todo(self, repo: Path, *arguments: str, allow_failure: bool = False):
        if arguments[0] == "bootstrap":
            return {"ok": True, "data": {"project_uuid": "parallel-project"}}
        if arguments[0] == "continue":
            return {"ok": True, "data": {
                "project_revision": 1,
                "claim": {"claim_token": f"toc_{self.agent}_claim"},
                "session": {"session_token": f"tos_{self.agent}_session"},
                "task": {"id": f"TASK-{self.agent}", "title": self.agent,
                         "objective": "independent frontier work", "next_action": "continue"},
                "scope": {"exclusive_paths": [f"src/{self.agent}"], "read_paths": [], "forbidden_paths": []},
                "interlocks": [], "gates": [],
            }}
        if arguments[0] == "pulse":
            self.pulses += 1
            return {"ok": True, "data": {"project_revision": self.pulses + 1}}
        if arguments[0] == "context":
            return {"ok": True, "data": {
                "project_revision": self.pulses + 1,
                "task": {"id": f"TASK-{self.agent}", "title": self.agent,
                         "objective": "independent frontier work", "next_action": "continue"},
                "scope": {"exclusive_paths": [f"src/{self.agent}"], "read_paths": [], "forbidden_paths": []},
                "gates": [],
            }}
        raise AssertionError(arguments)

    def worker(self, repo: Path, *arguments: str, timeout: float = 30):
        if "--collect" in arguments:
            execution = arguments[arguments.index("--collect") + 1]
            return self.admission.collect(execution)
        self.delegate_calls += 1
        mode = arguments[arguments.index("--mode") + 1]
        return self.admission.delegate(self.agent, mode)


def call(server, name: str, arguments: dict[str, object]) -> dict[str, object]:
    return asyncio.run(server._tool_manager.call_tool(name, arguments))


class FourAgentSafetyTests(unittest.TestCase):
    def test_two_slots_never_reduce_four_frontier_claims(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            admission = TwoSlotAdmission()
            backends = {
                agent: ParallelFakeBackend(root, root / f"state-{agent}", agent, admission)
                for agent in "ABCD"
            }
            servers = {agent: create_server(backend) for agent, backend in backends.items()}
            workflows = {
                agent: call(servers[agent], "next_task", {"repo_root": str(root)})["workflow_handle"]
                for agent in "ABCD"
            }

            first = call(servers["A"], "delegate_task", {
                "workflow_handle": workflows["A"], "mode": "auto"
            })
            second = call(servers["B"], "delegate_task", {
                "workflow_handle": workflows["B"], "mode": "auto"
            })
            third = call(servers["C"], "delegate_task", {
                "workflow_handle": workflows["C"], "mode": "auto"
            })
            fourth = call(servers["D"], "delegate_task", {
                "workflow_handle": workflows["D"], "mode": "auto"
            })

            self.assertEqual([first["status"], second["status"]], ["delegated", "delegated"])
            self.assertEqual([third["status"], fourth["status"]], ["local_unavailable", "local_unavailable"])
            self.assertEqual(admission.children_created, 2)
            self.assertEqual(admission.scopes_locked, 2)
            self.assertEqual(admission.unavailable_calls, 2)
            self.assertEqual(backends["C"].delegate_calls, 1)
            self.assertEqual(backends["D"].delegate_calls, 1)
            self.assertEqual(sum(item.blocked_states for item in backends.values()), 0)

            # Every parent capability remains active and editable after admission outcomes.
            for agent, workflow in workflows.items():
                record = backends[agent].store.get_workflow(workflow)
                self.assertEqual(record["task_id"], f"TASK-{agent}")
                refreshed = call(servers[agent], "inspect_task", {
                    "workflow_handle": workflow, "focus": "task"
                })
                self.assertEqual(refreshed["status"], "current")
                self.assertEqual(refreshed["scope"]["write"], [f"src/{agent}"])
                self.assertGreater(backends[agent].pulses, 0)

            running = call(servers["A"], "collect_delegation", {
                "delegation_handle": first["delegation_handle"]
            })
            self.assertEqual(running, {"status": "running", "instruction": "continue_frontier_or_collect_later",
                                       "poll_recommended": False})

            execution_a = backends["A"].store.get_delegation(first["delegation_handle"])["execution_id"]
            admission.complete(execution_a)
            accepted = call(servers["A"], "collect_delegation", {
                "delegation_handle": first["delegation_handle"]
            })
            self.assertEqual(accepted["status"], "accepted")
            self.assertFalse(accepted["parent_task_completed"])

            later = call(servers["C"], "delegate_task", {
                "workflow_handle": workflows["C"], "mode": "auto"
            })
            self.assertEqual(later["status"], "delegated")
            self.assertEqual(admission.children_created, 3)
            self.assertEqual(admission.scopes_locked, 2)
            self.assertEqual(backends["C"].delegate_calls, 2)


if __name__ == "__main__":
    unittest.main()
