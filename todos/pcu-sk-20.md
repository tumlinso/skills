

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-20: Integrate Skills kernel and compatibility changes

Task revision: `761`; current project revision is in `todo-status.md`.

## Objective
Integrate Skills-side changes while retaining Todo as kernel, preserving history, and leaving installed servers unchanged.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `.github/workflows`
- `exclusive`: `todo-orchestrator/pyproject.toml`
- `exclusive`: `todo-orchestrator/todo_orchestrator/__init__.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/mcp/server.py`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1`

## Dependencies
- `barrier`: `PCU-SK-CORE-BARRIER`
<!-- todo-orchestrator:v2-managed:end -->
