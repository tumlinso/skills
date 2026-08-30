"""Deprecated imports for Todo's canonical runtime-identity contract.

The compatibility package performs only the one-time source bootstrap needed
by old standalone installations. Identity, fingerprint, skew, and rebind rules
all live in :mod:`todo_orchestrator.runtime_identity`.
"""

from __future__ import annotations

from importlib import import_module
import json
import os
from pathlib import Path
import sys
from typing import Mapping


def locator_file(environment: Mapping[str, str] = os.environ) -> Path:
    data_home = Path(environment.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser()
    return data_home / "coding-workflow-mcp" / "skills-root.json"


def _configured_root(environment: Mapping[str, str]) -> Path:
    canonical = environment.get("PROJECT_CONTROL_SKILLS_ROOT")
    legacy = environment.get("CODING_WORKFLOW_SKILLS_ROOT")
    if canonical and legacy and Path(canonical).expanduser().resolve() != Path(legacy).expanduser().resolve():
        raise RuntimeError("runtime_identity_mismatch: configured Skills roots differ")
    selected = canonical or legacy
    if not selected:
        locator = locator_file(environment)
        try:
            selected = str(json.loads(locator.read_text(encoding="utf-8"))["skills_root"])
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError(
                "runtime_identity_mismatch: canonical Skills root is unavailable"
            ) from error
    return Path(selected).expanduser().resolve()


def _api(environment: Mapping[str, str] = os.environ):
    try:
        return import_module("todo_orchestrator.runtime_identity")
    except ModuleNotFoundError as error:
        if error.name not in {"todo_orchestrator", "todo_orchestrator.runtime_identity"}:
            raise
    # One release of source installs may not have Todo installed as a wheel.
    # Bootstrap its parent once; canonical Todo validates the resulting module.
    package_parent = _configured_root(environment) / "todo-orchestrator"
    value = str(package_parent)
    if value not in sys.path:
        sys.path.insert(0, value)
    return import_module("todo_orchestrator.runtime_identity")


def locate_skills_root(environment: Mapping[str, str] = os.environ) -> Path:
    return _api(environment).locate_skills_root(_configured_root(environment))


def bind_canonical_runtime(environment: Mapping[str, str] = os.environ):
    return _api(environment).bind_canonical_runtime(_configured_root(environment))


def validate_runtime(identity) -> None:
    _api().validate_runtime(identity)


def controlled_subprocess_env(identity, environment: Mapping[str, str] = os.environ) -> dict[str, str]:
    # Canonical Todo owns the environment contract. Preserve an explicitly
    # supplied compatibility environment only for variables it does not set.
    result = dict(environment)
    result.update(_api(environment).controlled_subprocess_env(identity))
    return result


def project_runtime_context(repo_root: str | Path, identity=None) -> dict[str, object]:
    return _api().project_runtime_context(repo_root, identity)


def __getattr__(name: str):
    if name in {"RuntimeIdentity", "RuntimeIdentityError"}:
        return getattr(_api(), name)
    raise AttributeError(name)


__all__ = [
    "bind_canonical_runtime", "controlled_subprocess_env", "locate_skills_root",
    "locator_file", "project_runtime_context", "validate_runtime",
]
