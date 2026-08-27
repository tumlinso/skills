

<!-- todo-orchestrator:v2-managed:start -->
# WFU-02: Implement forward-only kernel foundations and fixtures

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Add forward-only database foundations, shared internal service interfaces, capability lineage foundations, normalized semantic contracts, migration fixtures, and the frozen kernel contract consumed by parallel lanes.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/fixtures/workflow`
- `exclusive`: `todo-orchestrator/tests/test_child_execution_v2.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_foundation.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/db.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/migrations.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/foundation.py`
- `exclusive`: `workflow-unification/contracts/kernel-contract-v1.md`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator`

## Dependencies
- `task`: `WFU-01`
<!-- todo-orchestrator:v2-managed:end -->
