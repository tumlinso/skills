"""Canonical todo runtime identity shared across workflow process boundaries."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Mapping


class RuntimeIdentityError(RuntimeError):
    """A process is bound to a different todo runtime than the canonical locator."""

    code = "runtime_identity_mismatch"

    def __init__(self, message: str, *, expected: str, observed: str):
        super().__init__(message)
        self.expected = expected
        self.observed = observed


def locator_file(environment: Mapping[str, str] = os.environ) -> Path:
    data_home = Path(environment.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).expanduser()
    return data_home / "coding-workflow-mcp" / "skills-root.json"


def locate_skills_root(environment: Mapping[str, str] = os.environ) -> Path:
    configured = environment.get("CODING_WORKFLOW_SKILLS_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
    else:
        locator = locator_file(environment)
        if not locator.is_file():
            raise RuntimeIdentityError(
                "canonical Skills root is not configured; reinstall coding-workflow",
                expected=str(locator), observed="missing",
            )
        try:
            root = Path(str(json.loads(locator.read_text(encoding="utf-8"))["skills_root"])).expanduser().resolve()
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise RuntimeIdentityError(
                "canonical Skills root locator is invalid; reinstall coding-workflow",
                expected=str(locator), observed=type(exc).__name__,
            ) from exc
    package = root / "todo-orchestrator" / "todo_orchestrator"
    if not package.is_dir():
        raise RuntimeIdentityError(
            "canonical todo-orchestrator package is unavailable",
            expected=str(package), observed="missing",
        )
    return root


def _fingerprint(package: Path) -> str:
    digest = hashlib.sha256()
    for source in sorted(package.rglob("*.py")):
        digest.update(str(source.relative_to(package)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(source.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class RuntimeIdentity:
    skills_root: Path
    package_root: Path
    module_file: Path
    fingerprint: str

    def public(self) -> dict[str, str]:
        return {
            "skills_root": str(self.skills_root),
            "package_root": str(self.package_root),
            "module_file": str(self.module_file),
            "fingerprint": self.fingerprint,
        }


def _loaded_module_file() -> Path | None:
    module = sys.modules.get("todo_orchestrator")
    value = getattr(module, "__file__", None) if module is not None else None
    return Path(value).resolve() if value else None


def bind_canonical_runtime(environment: Mapping[str, str] = os.environ) -> RuntimeIdentity:
    root = locate_skills_root(environment)
    package = (root / "todo-orchestrator" / "todo_orchestrator").resolve()
    expected_module = (package / "__init__.py").resolve()
    observed = _loaded_module_file()
    if observed is not None and observed != expected_module:
        raise RuntimeIdentityError(
            "todo_orchestrator was imported from a non-canonical runtime; restart this process",
            expected=str(expected_module), observed=str(observed),
        )
    parent = str(package.parent)
    sys.path[:] = [item for item in sys.path if str(Path(item or ".").resolve()) != str(package.parent)]
    sys.path.insert(0, parent)
    __import__("todo_orchestrator")
    observed = _loaded_module_file()
    if observed != expected_module:
        raise RuntimeIdentityError(
            "Python did not bind the canonical todo_orchestrator runtime; restart this process",
            expected=str(expected_module), observed=str(observed),
        )
    identity = RuntimeIdentity(root, package, observed, _fingerprint(package))
    expected_fingerprint = environment.get("CODING_WORKFLOW_RUNTIME_FINGERPRINT")
    if expected_fingerprint and expected_fingerprint != identity.fingerprint:
        raise RuntimeIdentityError(
            "canonical todo runtime changed after process launch; restart this process",
            expected=expected_fingerprint, observed=identity.fingerprint,
        )
    return identity


def validate_runtime(identity: RuntimeIdentity) -> None:
    observed = _loaded_module_file()
    current = _fingerprint(identity.package_root)
    if observed != identity.module_file or current != identity.fingerprint:
        raise RuntimeIdentityError(
            "canonical todo runtime identity changed; restart this process",
            expected=f"{identity.module_file}:{identity.fingerprint}",
            observed=f"{observed}:{current}",
        )


def controlled_subprocess_env(identity: RuntimeIdentity, environment: Mapping[str, str] = os.environ) -> dict[str, str]:
    """Preserve documented state roots while excluding import/read-only contamination."""
    clean = dict(environment)
    clean.pop("PYTHONPATH", None)
    clean.pop("TODO_ORCHESTRATOR_READ_ONLY", None)
    clean["CODING_WORKFLOW_SKILLS_ROOT"] = str(identity.skills_root)
    clean["CODING_WORKFLOW_RUNTIME_FINGERPRINT"] = identity.fingerprint
    return clean


def project_runtime_context(repo_root: str | Path, identity: RuntimeIdentity | None = None) -> dict[str, str]:
    identity = identity or bind_canonical_runtime()
    validate_runtime(identity)
    from todo_orchestrator.config import project_paths, read_project
    from todo_orchestrator.migrations import DATABASE_MIGRATION_VERSION

    paths = project_paths(repo_root)
    project = read_project(paths.repo_root)
    return {
        **identity.public(),
        "database_migration_version": str(DATABASE_MIGRATION_VERSION),
        "project_uuid": str(project["project_uuid"]),
        "db_path": str(paths.db_file.resolve()),
    }
