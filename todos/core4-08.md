

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-08: Add CUDA benchmark registry and changed-code discovery

Task revision: `107`; current project revision is in `todo-status.md`.

## Objective
Let projects register build, correctness, benchmark, metric, resource, path, symbol, and target contracts once; discover matching campaigns from changed files, todo scopes, accepted local-worker patches, and ctxpp symbol identity; auto-queue only unambiguous matches.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
Implement registry validation and changed-code matching in new modules, then add thin controller commands without guessing among ambiguous production benchmarks.

## Ownership
- `exclusive`: `cuda/references/benchmark-registry.md`
- `exclusive`: `cuda/schemas/benchmark-registry-v1.schema.json`
- `exclusive`: `cuda/schemas/metric-v1.schema.json`
- `exclusive`: `cuda/scripts/cuda_controller.py`
- `exclusive`: `cuda/scripts/cuda_discovery.py`
- `exclusive`: `cuda/scripts/cuda_registry.py`
- `exclusive`: `cuda/tests/test_registry_discovery.py`
- `read`: `cpp-context-compiler/scripts/ctxpp`
- `read`: `cuda/tests/test_controller.py`
- `read`: `todo-orchestrator/todo_orchestrator/runtime`

## Dependencies
- `checkpoint`: `CORE4-RUNTIME-FROZEN`
- `checkpoint`: `CORE4-CTXPP-PACKET-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
