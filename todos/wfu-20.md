

<!-- todo-orchestrator:v2-managed:start -->
# WFU-20: Integrate workflow modules into todo services and compatibility surfaces

Task revision: `214`; current project revision is in `todo-status.md`.

## Objective
Integrate all core modules into shared service methods, CLI commands, schema migration dispatch, plan normalization, export, deterministic snapshots, restore, doctor, audit, projections, semantic reads, and existing lifecycle behavior; publish the normalized semantic read contract.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/schemas`
- `exclusive`: `todo-orchestrator/scripts/todo.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_integration.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_plan_snapshot.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/__init__.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/audit.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/child_execution.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/claims.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/cli.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/commands`
- `exclusive`: `todo-orchestrator/todo_orchestrator/gates.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/plan.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/projections.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/reporting.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/semantic`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/__init__.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `exclusive`: `workflow-unification/contracts/semantic-read-v1.md`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`

## Dependencies
- `task`: `WFU-16`
<!-- todo-orchestrator:v2-managed:end -->
