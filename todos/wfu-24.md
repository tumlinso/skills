<!-- todo-orchestrator:v2-managed:start -->
# WFU-24: Harden plan idempotence and canonical protocol integration seams

Task revision: `201`; current project revision is in `todo-status.md`.

## Objective
Preserve frozen interfaces across plan reapply, complete bounded v2 context and arrival contracts, wire immutable integration requests, and prove canonical kernel behavior before project-control and dogfood validation.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `serial`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_integration.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_plan_snapshot.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/plan.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/protocol.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`

## Dependencies
- `task`: `WFU-21`
<!-- todo-orchestrator:v2-managed:end -->
