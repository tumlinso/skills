

<!-- todo-orchestrator:v2-managed:start -->
# SK-AS1-GPU: Make warm observer models reclaimable by foreground work

Task revision: `923`; current project revision is in `todo-status.md`.

## Objective
Complete observer/skill residency participation in the existing host-global CUDA eviction/interlock protocol.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
Read SK-AS1-GPU in planning/adaptive-surface-v1/planning/outcomes.json. Verify producer receipts and pass every required case.

## Ownership
- `exclusive`: `cuda/scripts`
- `exclusive`: `cuda/tests`
- `exclusive`: `local-coding-worker`
- `exclusive`: `planning/adaptive-surface-v1`
- `exclusive`: `tests/as1`
- `exclusive`: `todo-orchestrator/todo_orchestrator/background/host.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/runtime/facade.py`
- `read`: `planning/adaptive-surface-v1`

## Dependencies
- `task`: `SK-AS1-RUNTIME`
<!-- todo-orchestrator:v2-managed:end -->
