from __future__ import annotations

import asyncio
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class ProtocolTests(unittest.TestCase):
    def test_initialize_list_and_invoke_all_seven_tools(self) -> None:
        fake_server = Path(__file__).with_name("fake_server.py")

        async def scenario() -> None:
            parameters = StdioServerParameters(command=sys.executable, args=[str(fake_server)])
            async with stdio_client(parameters) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    initialized = await session.initialize()
                    self.assertEqual(initialized.serverInfo.name, "coding-workflow")
                    self.assertIn("Call next_task once", (initialized.instructions or "")[:512])
                    listed = await session.list_tools()
                    self.assertEqual({tool.name for tool in listed.tools}, {
                        "next_task", "inspect_task", "delegate_task", "collect_delegation", "run_gates",
                        "recover_terminal_checkpoints", "finish_task",
                    })
                    claimed = await session.call_tool("next_task", {"repo_root": "."})
                    self.assertFalse(claimed.isError)
                    workflow = claimed.structuredContent["workflow_handle"]
                    inspected = await session.call_tool("inspect_task", {
                        "workflow_handle": workflow, "focus": "source", "target": "Widget", "intent": "edit",
                    })
                    self.assertEqual(inspected.structuredContent["status"], "available")
                    delegated = await session.call_tool("delegate_task", {
                        "workflow_handle": workflow, "mode": "auto", "target": "Widget",
                    })
                    self.assertEqual(delegated.structuredContent["status"], "delegated")
                    collected = await session.call_tool("collect_delegation", {
                        "delegation_handle": delegated.structuredContent["delegation_handle"],
                    })
                    self.assertEqual(collected.structuredContent["status"], "running")
                    gates = await session.call_tool("run_gates", {
                        "workflow_handle": workflow,
                    })
                    self.assertEqual(gates.structuredContent["status"], "passed")
                    recovered = await session.call_tool("recover_terminal_checkpoints", {
                        "repo_root": ".", "task_id": "T-1", "checkpoint_id": "C-1",
                    })
                    self.assertEqual(recovered.structuredContent["status"], "finalized")
                    finished = await session.call_tool("finish_task", {
                        "workflow_handle": workflow, "action": "complete", "disposition": "implemented",
                    })
                    self.assertEqual(finished.structuredContent["status"], "finished")

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
