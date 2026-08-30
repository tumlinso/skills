

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-11: Canonicalize the workflow front door and owner identity

Task revision: `739`; current project revision is in `todo-status.md`.

## Objective
Make project-control canonical for new automated ownership while accepting historical coding-workflow identities and preserving current exceptions.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_force_release.py`
- `exclusive`: `todo-orchestrator/tests/test_live_claim_override.py`
- `exclusive`: `todo-orchestrator/tests/test_workflow_front_door.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/claims.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/front_door.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/sessions.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/workflow/service.py`
- `read`: `todo-orchestrator/todo_orchestrator/workflow`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `checkpoint`: `PCU-SK-CONTRACTS-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
