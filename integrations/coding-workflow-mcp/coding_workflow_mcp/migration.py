"""Compatibility imports for Project Control repository migration."""

from __future__ import annotations

from os import PathLike
from typing import Any

from .compat import ProjectControlUnavailable, migration_api


class MigrationError(ProjectControlUnavailable):
    """Compatibility error used when Project Control is not installed."""


def migrate(
    repo: str | PathLike[str], *, apply: bool = False, remove: bool = False,
) -> dict[str, Any]:
    try:
        migration = migration_api()
    except ProjectControlUnavailable as error:
        raise MigrationError(str(error)) from error
    try:
        return migration.migrate(repo, apply=apply, remove=remove)
    except migration.MigrationError as error:
        raise MigrationError(str(error)) from error


__all__ = ["MigrationError", "migrate"]
