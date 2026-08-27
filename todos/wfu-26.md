

<!-- todo-orchestrator:v2-managed:start -->
# WFU-26: Complete the frozen workflow semantic read contract

Task revision: `231`; current project revision is in `todo-status.md`.

## Objective
Expose normalized immutable patch artifacts, synthesize recovery-needed state across authoritative claims, sessions, dispatches, children, gates, locks, resources, workspaces, and integration failures, and emit safe parallel groups only after dependency, interface, lock, resource, and scope checks.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_semantic_read.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/semantic/workflow.py`
- `read`: `todo-orchestrator/tests/v2_helpers.py`
- `read`: `todo-orchestrator/todo_orchestrator/semantic`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`
- `read`: `workflow-unification/contracts/semantic-read-v1.md`

## Dependencies
- `task`: `WFU-24`
<!-- todo-orchestrator:v2-managed:end -->
