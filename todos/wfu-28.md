

<!-- todo-orchestrator:v2-managed:start -->
# WFU-28: Restore resumable serial-lane state after release and recovery

Task revision: `242`; current project revision is in `todo-status.md`.

## Objective
Make first-class handoff, block, release, and owner recovery reconcile the current serial lane task and lane state transactionally so clean work can resume through next_task, while dirty recovery remains preserved and attention-required.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_lane_resume.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/recovery.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `read`: `todo-orchestrator/tests/test_workflow_integration.py`
- `read`: `todo-orchestrator/tests/test_workflow_recovery.py`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/lanes.py`

## Dependencies
- `task`: `WFU-27`
<!-- todo-orchestrator:v2-managed:end -->
