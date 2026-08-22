

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-04: Implement restricted todo child-execution core

Task revision: `46`; current project revision is in `todo-status.md`.

## Objective
Add generic child-execution authorization, restricted child tokens, subset scope leases, lifecycle state, heartbeat, attempts, recovery, and cancellation without granting parent completion or creating a second task graph.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Implement the smallest additive schema and CLI surface for child executions, then prove token privilege and recovery behavior.

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_child_execution_core.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/child_execution.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/commands/__init__.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/commands/child_execution.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/migrations.py`
- `read`: `todo-orchestrator/todo_orchestrator/claims.py`
- `read`: `todo-orchestrator/todo_orchestrator/ownership.py`
- `read`: `todo-orchestrator/todo_orchestrator/runtime`
- `read`: `todo-orchestrator/todo_orchestrator/sessions.py`

## Dependencies
- `checkpoint`: `CORE4-RUNTIME-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
