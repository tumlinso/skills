

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-09: Add CUDA compatible baselines, performance facts, and quiescence

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Replace first-result-only baseline semantics with accepted/previous/candidate/historical compatibility, store reusable performance facts, make profiler escalation decision-driven, adapt correctness repetition, and prove post-inference GPU quiescence before uncontaminated measurements.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `serial`
- Result: `-`

## Next Action
Implement new fact and compatibility modules, preserve raw evidence, and update controller classification without changing existing commands.

## Ownership
- `exclusive`: `cuda/references/performance-facts.md`
- `exclusive`: `cuda/schemas/performance-fact-v1.schema.json`
- `exclusive`: `cuda/scripts/cuda_baselines.py`
- `exclusive`: `cuda/scripts/cuda_controller.py`
- `exclusive`: `cuda/scripts/cuda_facts.py`
- `exclusive`: `cuda/scripts/cuda_quiescence.py`
- `exclusive`: `cuda/tests/test_performance_facts.py`
- `read`: `cuda/tests/test_controller.py`
- `read`: `todo-orchestrator/todo_orchestrator/runtime`

## Dependencies
- `checkpoint`: `CORE4-CUDA-CAMPAIGN-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
