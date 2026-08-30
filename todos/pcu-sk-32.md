

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-32: Atomically cut over the installed runtime

Task revision: `694`; current project revision is in `todo-status.md`.

## Objective
Install the validated candidate, make project-control the sole Codex MCP, switch observer service to the pin, verify health/shared authority, and automatically restore prior state on failure; exclude downstream migration and deletion.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `integration_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `unification/pcu-v1/evidence/cutover/pcu-sk-32.cutover.json`
- `read`: `.gitmodules`
- `read`: `project-control`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1`

## Dependencies
- `barrier`: `PCU-SK-VALIDATION-BARRIER`
<!-- todo-orchestrator:v2-managed:end -->
