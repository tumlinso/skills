<!-- todo-orchestrator:v2-managed:start -->
# WFU-27: Authorize isolated-merge overlap in claim readiness

Task revision: `220`; current project revision is in `todo-status.md`.

## Objective
Teach the shared claim/readiness authority to permit overlapping first-class task scopes only when both lanes have explicit isolated_merge contracts, active managed workspaces from the same base, one shared integration task, and an exclusive designated integrator destination; retain same-worktree exclusion everywhere else.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_isolated_claims.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/ownership.py`
- `read`: `todo-orchestrator/tests/v2_helpers.py`
- `read`: `todo-orchestrator/todo_orchestrator/readiness.py`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/workspaces.py`

## Dependencies
- `task`: `WFU-24`
<!-- todo-orchestrator:v2-managed:end -->
