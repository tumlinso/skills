

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-10: Add the explicit Todo read-only in-process port

Task revision: `761`; current project revision is in `todo-status.md`.

## Objective
Expose normalized read operations through a fail-closed in-process facade and prove no revision, snapshot, Git, or database-byte mutation.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_read_only_schema_compatibility.py`
- `exclusive`: `todo-orchestrator/tests/test_read_port.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/db.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/read_port.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/semantic/read_port.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `read`: `todo-orchestrator/todo_orchestrator/semantic`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `checkpoint`: `PCU-SK-CONTRACTS-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
