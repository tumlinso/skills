

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-23: Resolve fresh-clone validation blockers

Task revision: `739`; current project revision is in `todo-status.md`.

## Objective
Remove tracked non-relocatable CMake products, keep them ignored, and make candidate-plan dependency-complete while preserving deterministic local source installation.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `.gitignore`
- `exclusive`: `cpp-context-compiler/tool/build`
- `exclusive`: `tests/pcu_v1/test_harness.py`
- `exclusive`: `unification/pcu-v1/scripts/pcu_harness.py`
- `read`: `cpp-context-compiler`
- `read`: `local-coding-worker`
- `read`: `project-control`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1`

## Dependencies
- `task`: `PCU-SK-22`
<!-- todo-orchestrator:v2-managed:end -->
