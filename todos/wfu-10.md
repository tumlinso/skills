<!-- todo-orchestrator:v2-managed:start -->
# WFU-10: Runs, serial lanes, roles, dispatch, and scheduling

Task revision: `133`; current project revision is in `todo-status.md`.

## Objective
Implement durable first-class Codex runs, lane trees, ordered queues, role enforcement, dispatch identity, heartbeat, deterministic assignment, serial-lane constraints, and wait-cycle diagnostics without representing local children as lanes.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_runs_lanes.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/lanes.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/roles.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/runs.py`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/foundation.py`
- `read`: `workflow-unification/contracts/kernel-contract-v1.md`

## Dependencies
- `checkpoint`: `WFU-KERNEL-CONTRACT-V1`
<!-- todo-orchestrator:v2-managed:end -->
