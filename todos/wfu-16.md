

<!-- todo-orchestrator:v2-managed:start -->
# WFU-16: Harden cross-core authority and concurrency contracts

Task revision: `201`; current project revision is in `todo-status.md`.

## Objective
After all core lanes arrive, correct cross-module defects found by read-only integration review: authoritative integration-gate provenance, completion-bound rendezvous and canonical barrier composition, workspace reservation/provenance/immutability/final artifact rules, required workspace dispatch validation, child packet source-scope containment, composite fragment ownership, lossless message cursors and resolution deltas, and idempotent synchronization.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_v2_graph_coordination.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_context_fragments.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_messages_rendezvous.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_runs_lanes.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_workspaces.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/gates.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/graph.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/context_fragments.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/lanes.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/messages.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/rendezvous.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/workspaces.py`
- `read`: `todo-orchestrator/tests`
- `read`: `todo-orchestrator/todo_orchestrator`
- `read`: `workflow-unification/contracts`

## Dependencies
- `barrier`: `WFU-CORE-RENDEZVOUS`
<!-- todo-orchestrator:v2-managed:end -->
