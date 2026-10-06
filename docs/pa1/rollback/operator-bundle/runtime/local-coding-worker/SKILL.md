---
name: local-coding-worker
description: Navigation to Project Control's verified local observer runtime. Demand-only; reading this skill does not start a service or model.
---

# Local Coding Worker

The runtime is owned by Project Control. This skill is a navigation entrypoint, not a second implementation or delegation authority.

For ordinary research, implementation, tests, and review, use configured Codex subagents. Project Control may use its read-only observer through the existing central supervisor when an active parent task explicitly selects that path. The default is demand-only; opening this skill, importing `local_worker`, or checking runtime status does not start a service or load a model.

The legacy `local_worker.*` namespace binds only to Project Control's exact receiver manifest. Importing it requires the Project Control package to be installed and the receiver source or release manifest to pass validation. A missing or mismatched receiver fails closed. Legacy CLI scripts forward to the verified receiver.

Canonical implementation and contracts live under `project_control/local_runtime/` and are reached through `project_control.runtime_binding`. The Skills copies under `local_worker/`, `config/`, `schemas/`, and `references/` are rollback-preserved navigation/deprecation markers.

The observer remains read-only and job-scoped. It has no task lifecycle, sibling communication, architecture, commit, push, recursive-agent, or writable delegation authority. Internal maintenance contracts remain in the canonical runtime for compatibility history, while the supported coding CLI commands are unconditionally disabled at the receiver command boundary. This forwarder does not enable coding delegation.

Todo Orchestrator, CUDA resource admission, and ctxpp remain independent authorities. This skill does not copy, wrap, or grant access to those systems.
