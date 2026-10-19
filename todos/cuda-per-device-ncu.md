

<!-- todo-orchestrator:v2-managed:start -->
# CUDA-PER-DEVICE-NCU: Enable correctly scoped per-device NCU profiling

Task revision: `1042`; current project revision is in `todo-status.md`.

## Objective
Implement CPU-tested and native-qualified device-scoped NCU coordination in CUDA skill, preserving admission, legacy behavior, benchmark exclusion and cancellation. Do not modify Project Control allocator or KDA submodule skills.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
Develop on a bounded Skills branch, test per-UUID locks and marker ownership, deploy only the validated fix, then qualify overlapping native captures under root scheduling.

## Ownership
- `exclusive`: `cuda/references/execution`
- `exclusive`: `cuda/scripts/cuda_controller.py`
- `exclusive`: `cuda/scripts/profile_ncu.sh`
- `exclusive`: `cuda/scripts/with_benchmark_mutex.sh`
- `exclusive`: `cuda/tests`
- `read`: `cuda`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
