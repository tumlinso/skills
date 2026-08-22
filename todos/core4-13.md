

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-13: Implement priority-aware GPU service interlocks and preemption

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Extend the supported host resource facade minimally so active local delegation normally outranks background CUDA work, explicit clean CUDA foreground work overrides and drains local inference, idle model residency is lowest priority, preemption preserves task state, and topology bundles are discovered rather than hard-coded.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `integration_exclusive`
- Result: `-`

## Next Action
Add named priority classes and service-owner lifecycle without rewriting todo scheduling. Prove drain, eviction, quiescence, stale-owner recovery, and spare-island correctness behavior with simulated processes.

## Ownership
- `exclusive`: `cuda/scripts/cuda_controller.py`
- `exclusive`: `cuda/tests/test_core4_interlock.py`
- `exclusive`: `local-coding-worker/local_worker/service.py`
- `exclusive`: `local-coding-worker/references/resource-policy.md`
- `exclusive`: `local-coding-worker/tests/test_resource_policy.py`
- `exclusive`: `todo-orchestrator/references/runtime-resource-contract.md`
- `exclusive`: `todo-orchestrator/tests/test_core4_resource_policy.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/background/host.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/runtime/resources.py`
- `read`: `cuda/scripts/cuda_quiescence.py`
- `read`: `todo-orchestrator/todo_orchestrator/background/runner.py`

## Dependencies
- `checkpoint`: `CORE4-LOCAL-ADAPTERS-READY`
- `checkpoint`: `CORE4-CUDA-FACTS-FROZEN`
- `checkpoint`: `CORE4-RUNTIME-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
