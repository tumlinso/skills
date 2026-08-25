

<!-- todo-orchestrator:v2-managed:start -->
# CWM-08: Recover workflow capabilities across facade restarts

Task revision: `113`; current project revision is in `todo-status.md`.

## Objective
Durably resume a facade-owned active todo claim after MCP reinstall, restart, or turn boundary by issuing a fresh opaque workflow handle without duplicating the claim, corrupting revision state, or exposing raw todo secrets.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CWM-07`
<!-- todo-orchestrator:v2-managed:end -->
