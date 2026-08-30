

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-22: Build and smoke the unified candidate runtime

Task revision: `739`; current project revision is in `todo-status.md`.

## Objective
Build an isolated candidate from Skills plus the pinned submodule, resolving only missing Todo distribution metadata and a forward validated Project Control repin as necessary; verify both profiles and one authority without live registration/service changes.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `.gitmodules`
- `exclusive`: `project-control`
- `exclusive`: `todo-orchestrator/pyproject.toml`
- `exclusive`: `todo-orchestrator/tests/test_package_metadata.py`
- `exclusive`: `unification/pcu-v1/PCU_RELEASE.lock.json`
- `exclusive`: `unification/pcu-v1/evidence/candidate`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `local-coding-worker`
- `read`: `project-control`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1/contracts`
- `read`: `unification/pcu-v1/scripts`

## Dependencies
- `task`: `PCU-SK-21`
<!-- todo-orchestrator:v2-managed:end -->
