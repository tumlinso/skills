

<!-- todo-orchestrator:v2-managed:start -->
# WFU-11: Typed messages, cursors, rendezvous, and arrivals

Task revision: `231`; current project revision is in `todo-status.md`.

## Objective
Implement bounded typed first-class-lane messages, receipts and cursors, blocking questions and answers, durable decisions, rendezvous modes, idempotent arrivals, and atomic join readiness with parent-mediated child findings.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_messages_rendezvous.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/messages.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/rendezvous.py`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/foundation.py`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
