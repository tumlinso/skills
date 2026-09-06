"""Fail-closed identity for the canonical Skills/Todo runtime.

The identity is intentionally process-global: once a process has bound Todo to
one Skills checkout it may validate that binding, but it may not silently move
to another checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import threading
import warnings

from . import SCHEMA_VERSION
from .config import project_paths, read_project


CANONICAL_ROOT_VARIABLE = "PROJECT_CONTROL_SKILLS_ROOT"
LEGACY_ROOT_VARIABLE = "CODING_WORKFLOW_SKILLS_ROOT"
RUNTIME_FINGERPRINT_VARIABLE = "CODING_WORKFLOW_RUNTIME_FINGERPRINT"
CONTRACT = "PCU-RUNTIME-IDENTITY/1"


class RuntimeIdentityError(RuntimeError):
    """A configured or previously bound runtime does not match this package."""

    code = "runtime_identity_mismatch"

    def __init__(self, message: str, *, expected: object = None, observed: object = None):
        super().__init__(message)
        self.expected = expected
        self.observed = observed
        self.details = {
            key: value for key, value in (("expected", expected), ("observed", observed))
            if value is not None
        }


@dataclass(frozen=True)
class RuntimeIdentity:
    contract: str
    skills_root: Path
    package_root: Path
    package_source: Path
    todo_schema_version: int
    fingerprint: str

    def public(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "skills_root": str(self.skills_root),
            "package_root": str(self.package_root),
            "package_source": str(self.package_source),
            "todo_schema_version": self.todo_schema_version,
            "fingerprint": self.fingerprint,
        }


_binding_lock = threading.Lock()
_bound_identity: RuntimeIdentity | None = None


def _resolved(value: str | Path) -> Path:
    return Path(value).expanduser().resolve()


def _locator_root() -> Path | None:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")).expanduser()
    locator = data_home / "coding-workflow-mcp/skills-root.json"
    if not locator.is_file():
        return None
    try:
        payload = json.loads(locator.read_text(encoding="utf-8"))
        value = payload.get("skills_root")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise RuntimeIdentityError(f"invalid compatibility runtime locator: {locator}") from exc
    if not isinstance(value, str) or not value.strip():
        raise RuntimeIdentityError(f"invalid compatibility runtime locator: {locator}")
    warnings.warn(
        f"{locator} is a compatibility locator; configure {CANONICAL_ROOT_VARIABLE}",
        DeprecationWarning,
        stacklevel=3,
    )
    return _resolved(value)


def locate_skills_root(explicit_root: str | Path | None = None) -> Path:
    """Resolve one Skills root while rejecting conflicting configuration."""

    explicit = _resolved(explicit_root) if explicit_root is not None else None
    canonical_value = os.environ.get(CANONICAL_ROOT_VARIABLE)
    legacy_value = os.environ.get(LEGACY_ROOT_VARIABLE)
    canonical = _resolved(canonical_value) if canonical_value else None
    legacy = _resolved(legacy_value) if legacy_value else None

    if canonical is not None and legacy is not None and canonical != legacy:
        raise RuntimeIdentityError(
            f"{CANONICAL_ROOT_VARIABLE} and {LEGACY_ROOT_VARIABLE} identify different runtimes",
            expected=str(canonical), observed=str(legacy),
        )
    configured = canonical or legacy
    if explicit is not None and configured is not None and explicit != configured:
        raise RuntimeIdentityError(
            "explicit Skills root conflicts with configured runtime",
            expected=str(configured), observed=str(explicit),
        )
    if legacy is not None and canonical is None:
        warnings.warn(
            f"{LEGACY_ROOT_VARIABLE} is deprecated; use {CANONICAL_ROOT_VARIABLE}",
            DeprecationWarning,
            stacklevel=2,
        )

    selected = explicit or configured or _locator_root()
    if selected is None:
        inferred = Path(__file__).resolve().parents[2]
        if (inferred / "todo-orchestrator" / "todo_orchestrator" / "__init__.py").is_file():
            selected = inferred
    if selected is None:
        raise RuntimeIdentityError(
            f"canonical Skills root is unavailable; set {CANONICAL_ROOT_VARIABLE}"
        )
    return selected


def _hash_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise RuntimeIdentityError(f"runtime source is unreadable: {path}") from exc


def _release_digest(root: Path, package_root: Path) -> str | None:
    manifest = os.environ.get("PROJECT_CONTROL_RELEASE_MANIFEST")
    pinned = os.environ.get("PROJECT_CONTROL_RELEASE_DIGEST")
    if not manifest and not pinned:
        return None
    def fingerprint(package: Path) -> str:
        digest = hashlib.sha256()
        for path in sorted(package.rglob("*.py")):
            if path.is_file():
                digest.update(path.relative_to(package).as_posix().encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
        return digest.hexdigest()
    try:
        if not manifest or not pinned:
            raise ValueError("incomplete release binding")
        raw = Path(manifest).read_bytes()
        data = json.loads(raw)
        if hashlib.sha256(raw).hexdigest() != pinned or data["schema_version"] != 2:
            raise ValueError("release manifest mismatch")
        if Path(data["skills_root"]).resolve() != root:
            raise ValueError("release Skills root mismatch")
        expected = data["todo_runtime_fingerprint"]
        if fingerprint(package_root) != expected or fingerprint(root / "todo-orchestrator" / "todo_orchestrator") != expected:
            raise ValueError("release Todo package mismatch")
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeIdentityError("Invalid Todo release binding", observed=str(error)) from error
    return pinned


def _candidate_identity(skills_root: Path) -> RuntimeIdentity:
    root = skills_root.resolve()
    expected_package = (root / "todo-orchestrator" / "todo_orchestrator").resolve()
    package_root = Path(__file__).resolve().parent
    package_source = (package_root / "__init__.py").resolve()
    if not (expected_package / "__init__.py").is_file():
        raise RuntimeIdentityError(
            "configured Skills root does not contain Todo Orchestrator",
            expected=str(expected_package / "__init__.py"), observed="missing",
        )
    release_digest = _release_digest(root, package_root)
    if package_root != expected_package and release_digest is None:
        raise RuntimeIdentityError(
            "imported Todo package is not the configured Skills runtime",
            expected=str(expected_package), observed=str(package_root),
        )
    payload = {
        "contract": CONTRACT,
        "skills_root": str(root),
        "package_root": str(package_root),
        "todo_schema_version": SCHEMA_VERSION,
        "package_init_sha256": _hash_file(package_source),
        "runtime_identity_sha256": _hash_file(Path(__file__).resolve()),
    }
    if release_digest:
        payload["release_digest"] = release_digest
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return RuntimeIdentity(
        contract=CONTRACT,
        skills_root=root,
        package_root=package_root,
        package_source=package_source,
        todo_schema_version=SCHEMA_VERSION,
        fingerprint=fingerprint,
    )


def bind_canonical_runtime(skills_root: str | Path | None = None) -> RuntimeIdentity:
    """Bind this process to exactly one verified Todo runtime."""

    candidate = _candidate_identity(locate_skills_root(skills_root))
    expected_fingerprint = os.environ.get(RUNTIME_FINGERPRINT_VARIABLE)
    if expected_fingerprint and expected_fingerprint != candidate.fingerprint:
        raise RuntimeIdentityError(
            "runtime fingerprint does not match the launched environment",
            expected=expected_fingerprint, observed=candidate.fingerprint,
        )
    global _bound_identity
    with _binding_lock:
        if _bound_identity is not None and _bound_identity != candidate:
            raise RuntimeIdentityError(
                "runtime rebinding is forbidden; restart the process",
                expected=_bound_identity.public(), observed=candidate.public(),
            )
        _bound_identity = candidate
    return candidate


def validate_runtime(identity: RuntimeIdentity) -> None:
    """Recompute and compare the current source and process binding."""

    if not isinstance(identity, RuntimeIdentity):
        raise RuntimeIdentityError("unrecognized runtime identity object")
    candidate = _candidate_identity(identity.skills_root)
    with _binding_lock:
        bound = _bound_identity
    if bound is None or bound != identity or candidate != identity:
        raise RuntimeIdentityError(
            "runtime identity changed after initialization; restart the process",
            expected=identity.public(), observed=candidate.public(),
        )


def controlled_subprocess_env(identity: RuntimeIdentity) -> dict[str, str]:
    """Return a child environment pinned to the same verified runtime."""

    validate_runtime(identity)
    environment = dict(os.environ)
    root = str(identity.skills_root)
    environment[CANONICAL_ROOT_VARIABLE] = root
    # Keep the old variable for one compatibility window. It is an alias to the
    # same root, never an independently selected authority.
    environment[LEGACY_ROOT_VARIABLE] = root
    environment[RUNTIME_FINGERPRINT_VARIABLE] = identity.fingerprint
    environment["PYTHONPATH"] = str(identity.package_root.parent)
    return environment


def project_runtime_context(
    repo_root: str | Path, identity: RuntimeIdentity | None = None,
) -> dict[str, object]:
    """Describe the Todo authority attached to one bootstrapped repository."""

    runtime = identity or bind_canonical_runtime()
    validate_runtime(runtime)
    paths = project_paths(repo_root)
    project = read_project(paths.repo_root)
    return {
        **runtime.public(),
        "project_uuid": str(project["project_uuid"]),
        "repo_root": str(paths.repo_root),
        "db_path": str(paths.db_file),
    }


def _reset_for_testing() -> None:
    global _bound_identity
    with _binding_lock:
        _bound_identity = None


__all__ = [
    "CANONICAL_ROOT_VARIABLE", "CONTRACT", "LEGACY_ROOT_VARIABLE",
    "RUNTIME_FINGERPRINT_VARIABLE", "RuntimeIdentity", "RuntimeIdentityError",
    "bind_canonical_runtime", "controlled_subprocess_env", "locate_skills_root",
    "project_runtime_context", "validate_runtime",
]
