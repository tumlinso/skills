<!-- todo-orchestrator:v2-managed:start -->
# SK-MOM-RECOVERY-001: Preserve verified generated projections during producer recovery

Task revision: `1026`; current project revision is in `todo-status.md`.

## Objective
Fix the concrete moments producer completion/recovery blocker without accepting material dirt or modifying global installed runtime. Qualify the fix and use it only through the reviewed development maintenance CLI.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_projection_recovery.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/git_state.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/projection_state.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/recovery.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `forbidden`: `.todo-orchestrator`
- `forbidden`: `cuda`
- `forbidden`: `todo-status.md`
- `forbidden`: `todos`
- `forbidden`: `todos.md`
- `read`: `AGENTS.md`
- `read`: `integrations`
- `read`: `todo-orchestrator`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
