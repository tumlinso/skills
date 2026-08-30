

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-14: Reduce coding-workflow-mcp to a compatibility alias

Task revision: `761`; current project revision is in `todo-status.md`.

## Objective
Forward old executable/admin entry points to verified Project Control while retaining fail-safe fallback and removing independent backend semantics without deleting the package.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `.github/workflows/coding-workflow-mcp.yml`
- `exclusive`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `checkpoint`: `PCU-SK-CONTRACTS-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
