"""Supported, additive cross-skill runtime facade."""

from .contracts import (
    ContractError,
    normalize_artifact_ref,
    normalize_command_spec,
    normalize_evidence_summary,
    normalize_resource_request,
    normalize_source_identity,
)
from .facade import ArtifactFacade, HostResourceFacade, JobFacade, RuntimeFacade, SnapshotFacade
from .source import capture_source_identity

__all__ = [
    "ArtifactFacade",
    "ContractError",
    "HostResourceFacade",
    "JobFacade",
    "RuntimeFacade",
    "SnapshotFacade",
    "capture_source_identity",
    "normalize_artifact_ref",
    "normalize_command_spec",
    "normalize_evidence_summary",
    "normalize_resource_request",
    "normalize_source_identity",
]
