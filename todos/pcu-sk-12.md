<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-12: Consolidate runtime identity and compatibility variables

Task revision: `249`; current project revision is in `todo-status.md`.

## Objective
Provide one reusable identity contract, canonical and legacy variables, skew/rebind rejection, and preserved local-worker/background behavior.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `local-coding-worker/local_worker/canonical_runtime.py`
- `exclusive`: `local-coding-worker/tests/test_canonical_runtime.py`
- `exclusive`: `todo-orchestrator/tests/test_background_runtime.py`
- `exclusive`: `todo-orchestrator/tests/test_runtime_identity.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/runtime_identity.py`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `checkpoint`: `PCU-SK-CONTRACTS-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
