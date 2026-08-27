"""Compatibility import for the canonical MCP server factory."""

from ._canonical import canonical_server


def create_server():
    return canonical_server()


__all__ = ["create_server"]
