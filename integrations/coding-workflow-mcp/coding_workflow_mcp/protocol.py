"""Official-SDK smoke for active native routing and preserved internal contracts."""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


EXPECTED_WORKFLOW_TOOLS = {
    "next_task", "inspect_task", "coordinate_task", "delegate_task",
    "collect_delegation", "finish_task",
}

EXPECTED_NATIVE_TOOLS = EXPECTED_WORKFLOW_TOOLS - {"delegate_task", "collect_delegation"}


async def smoke(command: str, skills_root: str) -> dict[str, object]:
    parameters = StdioServerParameters(
        command=command,
        args=["-m", "coding_workflow_mcp"],
        env={**os.environ, "CODING_WORKFLOW_SKILLS_ROOT": skills_root},
    )
    async with stdio_client(parameters) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            initialized = await session.initialize()
            tools = await session.list_tools()
    names = {tool.name for tool in tools.tools}
    instructions = initialized.instructions or ""
    return {
        "ok": EXPECTED_NATIVE_TOOLS <= names and not names & {"delegate_task", "collect_delegation"},
        "server": initialized.serverInfo.name,
        "tools": sorted(names),
        "workflow_tools": sorted(EXPECTED_WORKFLOW_TOOLS),
        "active_workflow_tools": sorted(EXPECTED_NATIVE_TOOLS),
        "temporarily_inactive": ["collect_delegation", "delegate_task"],
        "instructions_bytes": len(instructions.encode("utf-8")),
    }


# Historical import name. It identifies the six required workflow contracts,
# not the complete Project Control Codex profile (which also has rich reads).
EXPECTED_TOOLS = EXPECTED_WORKFLOW_TOOLS


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True)
    parser.add_argument("--skills-root", required=True)
    arguments = parser.parse_args()
    result = asyncio.run(smoke(arguments.command, arguments.skills_root))
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    raise SystemExit(0 if result["ok"] else 2)


if __name__ == "__main__":
    main()
