"""Temporary ``coding-workflow`` entry-point compatibility.

Project Control is the product. This module contains only entry-point routing;
it never catches a Project Control startup or runtime-identity failure and it
does not implement an MCP tool, workflow transaction, claim, or recovery rule.
"""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Sequence


class ProjectControlUnavailable(RuntimeError):
    """The compatibility alias cannot find the Project Control distribution."""


def _project_control_module(name: str) -> ModuleType | None:
    """Import Project Control, distinguishing product absence from breakage."""

    try:
        return import_module(name)
    except ModuleNotFoundError as error:
        # Only absence of the product itself activates the bounded fallback.
        # Missing dependencies inside an installed product must fail closed.
        if error.name in {"project_control", name}:
            return None
        raise


def project_control_available() -> bool:
    return _project_control_module("project_control") is not None


def run_codex(argv: Sequence[str] | None = None) -> int:
    """Run the Project Control Codex profile under the historical executable."""

    cli = _project_control_module("project_control.cli")
    # `_serve_profile` is the PCU trusted-startup composition seam. Its
    # absence identifies the pre-PCU observer-only package, not a candidate.
    if cli is None or not callable(getattr(cli, "_serve_profile", None)):
        from ._canonical import run_fallback_server

        return run_fallback_server()
    arguments = ["serve", "codex", *(list(argv) if argv is not None else [])]
    return int(cli.main(arguments))


def run_admin(argv: Sequence[str] | None = None) -> int:
    """Forward the historical owner command to Project Control administration."""

    admin = _project_control_module("project_control.admin")
    if admin is None:
        from ._canonical import run_fallback_admin

        return run_fallback_admin(argv)
    return int(admin.main(argv))


def migration_api() -> ModuleType:
    """Resolve repository migration exclusively from Project Control."""

    migration = _project_control_module("project_control.migration")
    if migration is None:
        raise ProjectControlUnavailable(
            "Project Control is required for repository migration; the compatibility "
            "package does not contain a second migration implementation"
        )
    return migration


__all__ = [
    "ProjectControlUnavailable",
    "migration_api",
    "project_control_available",
    "run_admin",
    "run_codex",
]
