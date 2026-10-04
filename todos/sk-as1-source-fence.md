

<!-- todo-orchestrator:v2-managed:start -->
# SK-AS1-SOURCE-FENCE: Enforce trusted source verifier for local publication anchors

Task revision: `966`; current project revision is in `todo-status.md`.

## Objective
Close the reproduced local-source callback bypass during claim-scoped publication, preserving native fallback only when no trusted verifier is configured.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
Route all anchored source verification through the startup-owned verifier when present, qualify local/foreign denial and no-verifier fallback in disposable fixtures, and return source-bound receipt for PC CONTROL.

## Ownership
- `exclusive`: `docs/as1-source-fence.md`
- `exclusive`: `todo-orchestrator/tests/test_as1_source_fence.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/project_amendments.py`
- `read`: `docs/as1-foreign-source-port.md`
- `read`: `todo-orchestrator/todo_orchestrator/service.py`

## Dependencies
- `task`: `SK-AS1-SEMANTIC-PORT`
<!-- todo-orchestrator:v2-managed:end -->
