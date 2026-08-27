

<!-- todo-orchestrator:v2-managed:start -->
# WFU-14: Unified owner recovery engine and administrator command

Task revision: `171`; current project revision is in `todo-status.md`.

## Objective
Implement one interactive owner-only recovery engine covering first-class dispatches and distinct subordinate child degradation, with live-process refusal, dirty artifact preservation, idempotent terminal reconciliation, audit, and no approval-token round trip.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_recovery.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/admin.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/recovery.py`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator/todo_orchestrator/claims.py`
- `read`: `todo-orchestrator/todo_orchestrator/completion.py`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
