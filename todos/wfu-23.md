

<!-- todo-orchestrator:v2-managed:start -->
# WFU-23: Correct completed-program semantic-state selection

Task revision: `208`; current project revision is in `todo-status.md`.

## Objective
Fix the recorded semantic-state regression so current-only selection retains the most recently completed parent-defined program rather than an unrelated terminal task, while preserving read-only behavior and generic lifecycle filtering.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_semantic_state.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/semantic`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator`

## Dependencies
- `task`: `WFU-20`
<!-- todo-orchestrator:v2-managed:end -->
