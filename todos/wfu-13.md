

<!-- todo-orchestrator:v2-managed:start -->
# WFU-13: Managed isolated workspaces and integration queues

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Implement explicit workspace ownership modes, first-class lane worktree records, immutable patch and commit artifacts, integration queues, base enforcement, conflict preservation, and cleanup eligibility while retaining subordinate child scope leases.

## State
- Lifecycle: `in_progress`
- Execution: `claimed`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_workspaces.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/workspaces.py`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator/todo_orchestrator/git_state.py`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
