"""Deprecated factory for the bounded pre-cutover fallback only."""

from ._canonical import canonical_server


def create_server():
    """Return Todo's canonical server adapter, never a shim-owned backend."""

    return canonical_server()


__all__ = ["create_server"]
