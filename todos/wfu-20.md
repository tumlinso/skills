

<!-- todo-orchestrator:v2-managed:start -->
# WFU-20: Integrate workflow modules into todo services and compatibility surfaces

Task revision: `146`; current project revision is in `todo-status.md`.

## Objective
Integrate all core modules into shared service methods, CLI commands, schema migration dispatch, plan normalization, export, deterministic snapshots, restore, doctor, audit, projections, semantic reads, and existing lifecycle behavior; publish the normalized semantic read contract.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `integration_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/schemas`
- `exclusive`: `todo-orchestrator/scripts/todo.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_integration.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/commands`
- `exclusive`: `todo-orchestrator/todo_orchestrator/plans.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/projections.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/semantic.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/snapshots.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/__init__.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `exclusive`: `workflow-unification/contracts/semantic-read-v1.md`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`

## Dependencies
- `barrier`: `WFU-CORE-RENDEZVOUS`
<!-- todo-orchestrator:v2-managed:end -->
