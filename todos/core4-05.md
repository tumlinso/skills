

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-05: Integrate child evidence, gates, acceptance, and capsule surfacing

Task revision: `243`; current project revision is in `todo-status.md`.

## Objective
Let child executions run only authorized gates, attach evidence and artifacts, return compact completed/needs_codex/no_change/failed results, surface ready results in the next todo capsule, and require guarded parent acceptance before current-source completion.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Wire child results into service/context/reporting and publish the stable child-execution contract. Keep normal continue output unchanged when no child result is ready.

## Ownership
- `exclusive`: `todo-orchestrator/references/child-execution-contract.md`
- `exclusive`: `todo-orchestrator/schemas/child-execution-v1.schema.json`
- `exclusive`: `todo-orchestrator/tests/test_child_execution_integration.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/context.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/gates.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/reporting.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `read`: `todo-orchestrator/todo_orchestrator/child_execution.py`
- `read`: `todo-orchestrator/todo_orchestrator/evidence.py`

## Dependencies
- `checkpoint`: `CORE4-CHILD-CORE-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
