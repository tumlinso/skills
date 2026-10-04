

<!-- todo-orchestrator:v2-managed:start -->
# SK-AS1-CAPABILITY-PUBLICATION: Connect canonical opaque workflow handles to scoped semantic publication

Task revision: `929`; current project revision is in `todo-status.md`.

## Objective
Expose a supported authenticated canonical publication port without raw claim credential recovery, preserving role/operation/repository/task/source authorization and generic context fragment behavior.

## State
- Lifecycle: `in_progress`
- Execution: `claimed`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
Implement authenticated opaque-handle semantic publication with canonical in-transaction role, active claim, ownership and source checks, disposable native fixtures, root-reviewed boundary, and paired PC surface handoff.

## Ownership
- `exclusive`: `docs/as1-capability-publication.md`
- `exclusive`: `todo-orchestrator/tests/test_as1_capability_publication.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/project_amendments.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow`
- `read`: `planning/adaptive-surface-v1`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`

## Dependencies
- `task`: `SK-AS1-SOURCE-FRESHNESS`
<!-- todo-orchestrator:v2-managed:end -->
