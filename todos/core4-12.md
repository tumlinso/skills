

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-12: Implement isolated writable worktrees and guarded acceptance

Task revision: `100`; current project revision is in `todo-status.md`.

## Objective
Add detached worktree materialization from exact source identity, dirty overlay application, subset write-scope enforcement, baseline gates, external verification, patch artifacts, stale detection, guarded acceptance into the current primary worktree, and current-source acceptance gates.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
Implement writable mechanics independently of any real model. Use a deterministic fake worker to prove patch and conflict behavior.

## Ownership
- `exclusive`: `local-coding-worker/local_worker/acceptance.py`
- `exclusive`: `local-coding-worker/local_worker/verification.py`
- `exclusive`: `local-coding-worker/local_worker/workspace.py`
- `exclusive`: `local-coding-worker/references/writable-work-contract.md`
- `exclusive`: `local-coding-worker/tests/test_writable_work.py`
- `read`: `contracts/source-identity-v1.schema.json`
- `read`: `todo-orchestrator/todo_orchestrator/child_execution.py`
- `read`: `todo-orchestrator/todo_orchestrator/runtime`

## Dependencies
- `checkpoint`: `CORE4-LOCAL-READONLY-FROZEN`
- `checkpoint`: `CORE4-TODO-DELEGATION-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
