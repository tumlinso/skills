

<!-- todo-orchestrator:v2-managed:start -->
# SK-AS1-SOURCE-FRESHNESS: Preserve local content freshness after source-backed amendments

Task revision: `966`; current project revision is in `todo-status.md`.

## Objective
Avoid implicit same-authority revision self-invalidation while preserving trusted source fencing, explicit caller pins, and exact foreign authority stamps.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
Correct the reproduced source-backed local orientation freshness regression and qualify paired PC control against exact final source.

## Ownership
- `exclusive`: `docs/as1-source-fence.md`
- `exclusive`: `todo-orchestrator/tests/test_as1_source_fence.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/project_amendments.py`
- `read`: `docs/as1-foreign-source-port.md`
- `read`: `todo-orchestrator/todo_orchestrator/service.py`

## Dependencies
- `task`: `SK-AS1-SOURCE-FENCE`
<!-- todo-orchestrator:v2-managed:end -->
