from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from coding_workflow_mcp.protocol import EXPECTED_TOOLS


class ProtocolTests(unittest.TestCase):
    def test_initialize_discovers_exact_six_canonical_tools(self) -> None:
        package = Path(__file__).resolve().parents[1]
        skills = package.parents[1]

        async def scenario() -> None:
            parameters = StdioServerParameters(
                command=sys.executable,
                args=["-m", "coding_workflow_mcp"],
                env={**os.environ, "PYTHONPATH": str(package), "CODING_WORKFLOW_SKILLS_ROOT": str(skills)},
            )
            async with stdio_client(parameters) as streams:
                async with ClientSession(*streams) as session:
                    initialized = await session.initialize()
                    tools = await session.list_tools()
            self.assertEqual(initialized.serverInfo.name, "coding-workflow")
            self.assertEqual({tool.name for tool in tools.tools}, EXPECTED_TOOLS)
            self.assertIn("only ordinary workflow protocol", initialized.instructions or "")
            self.assertNotIn("recover_terminal_checkpoints", EXPECTED_TOOLS)
            self.assertNotIn("run_gates", EXPECTED_TOOLS)

        asyncio.run(scenario())


if __name__ == "__main__":
    unittest.main()
