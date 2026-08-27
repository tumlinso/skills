

<!-- todo-orchestrator:v2-managed:start -->
# WFU-12: Versioned context fragments and bounded composition

Task revision: `223`; current project revision is in `todo-status.md`.

## Objective
Implement hashed versioned run, lane, task, decision, delta, and source-reference fragments with targeted invalidation, strict response budgets, and deliberately narrower local-child packets.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_context_fragments.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/context_fragments.py`
- `read`: `cpp-context-compiler`
- `read`: `local-coding-worker`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
