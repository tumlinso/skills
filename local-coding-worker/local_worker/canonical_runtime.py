"""Bridge local-worker startup to coding-workflow's canonical runtime contract."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys


class CanonicalRuntimeError(RuntimeError):
    code = "runtime_identity_mismatch"


def _api():
    try:
        from coding_workflow_mcp import runtime_identity
        return runtime_identity
    except ModuleNotFoundError:
        configured = os.environ.get("CODING_WORKFLOW_SKILLS_ROOT")
        if configured:
            root = Path(configured).expanduser().resolve()
        else:
            data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser()
            locator = data_home / "coding-workflow-mcp/skills-root.json"
            root = Path(str(json.loads(locator.read_text(encoding="utf-8"))["skills_root"])).expanduser().resolve()
        integration = root / "integrations/coding-workflow-mcp"
        sys.path.insert(0, str(integration))
        from coding_workflow_mcp import runtime_identity
        return runtime_identity


def bind(repo_root: str | Path):
    api = _api()
    try:
        identity = api.bind_canonical_runtime()
    except Exception as exc:
        if getattr(exc, "code", None) == "runtime_identity_mismatch":
            raise CanonicalRuntimeError(f"runtime_identity_mismatch: {exc}") from exc
        raise
    try:
        context = api.project_runtime_context(repo_root, identity)
    except Exception as exc:
        if getattr(exc, "code", None) != "project_not_bootstrapped":
            raise
        context = identity.public()
    return identity, context


def validate(identity) -> None:
    try:
        _api().validate_runtime(identity)
    except Exception as exc:
        if getattr(exc, "code", None) == "runtime_identity_mismatch":
            raise CanonicalRuntimeError(f"runtime_identity_mismatch: {exc}") from exc
        raise


def subprocess_environment(identity) -> dict[str, str]:
    return _api().controlled_subprocess_env(identity)
