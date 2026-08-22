

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-01: Archive the previous ledger and bootstrap CORE4

Task revision: `243`; current project revision is in `todo-status.md`.

## Objective
Record that the previous completed todo program was exported and archived outside the worktree, stale legacy projections were removed, a fresh v2 project identity was created, and this plan was transactionally applied.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `project_exclusive`
- Result: `validated`

## Next Action
Bootstrap complete; implementation begins at CORE4-02.

## Ownership
- `exclusive`: `.gitignore`
- `exclusive`: `.todo-orchestrator/core4.plan.json`
- `exclusive`: `.todo-orchestrator/project.json`
- `exclusive`: `.todo-orchestrator/state.snapshot.json`
- `exclusive`: `AGENTS.md`
- `exclusive`: `todo-status.md`
- `exclusive`: `todos.md`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
