"""Native registration policy; internal workflow protocol remains unchanged."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

TEMPORARILY_INACTIVE = frozenset({"delegate_task", "collect_delegation"})


def routing_policy():
    return {name: {"status": "temporarily_inactive", "preserve_implementation": True,
            "reason": "local workers are reserved for read-only Project Control observer jobs",
            "reactivation": "explicit operator decision; no timed reactivation"}
            for name in sorted(TEMPORARILY_INACTIVE)}


class NativeRoutingFastMCP(FastMCP):
    """Keep dormant handlers internally, but refuse model-facing dispatch."""
    @property
    def routing_policy(self):
        return routing_policy()

    async def list_tools(self):
        return [tool for tool in await super().list_tools() if tool.name not in TEMPORARILY_INACTIVE]

    async def call_tool(self, name, arguments):
        if name in TEMPORARILY_INACTIVE:
            raise ToolError(f"temporarily_inactive: {name}; reactivation requires explicit operator decision")
        return await super().call_tool(name, arguments)


def bind_native_routing(server: FastMCP) -> NativeRoutingFastMCP:
    """Share canonical handlers without copying or changing kernel methods.

    The SDK registers these subclass methods during construction. Filtering a
    Python list after construction would leave the actual MCP dispatch open.
    """
    native = NativeRoutingFastMCP(server.name, instructions=server.instructions, log_level="ERROR")
    native._tool_manager = server._tool_manager
    native._resource_manager = server._resource_manager
    native._prompt_manager = server._prompt_manager
    return native
