# NVHPC Tradeoffs On V100

## Default Rule

Prefer raw CUDA/C++ plus NVIDIA libraries when:

- the hot path needs exact layout control
- data movement must be explicit
- fusion and staging decisions are performance-critical
- the real value comes from cuBLAS, cuSPARSE, NCCL, CUTLASS, or hand-tuned kernels anyway

Use an NVHPC abstraction only when it:

- removes enough engineering cost to matter
- does not hide critical data movement
- still permits the right library interop

For V100-specific peak chasing, assume the burden of proof is on the abstraction, not on raw CUDA/C++.

## Why This Matters On V100

V100 is old enough that overheads from hidden transfers, poor memory mode choices, or extra runtime layers can matter materially. The card is fast enough to expose control-path waste.

## Good Uses

- NVC++ for a mostly C++ codebase that still needs explicit CUDA/library interop
- NVTX instrumentation through the available toolchain
- targeted directive-based offload for non-critical or rapidly changing code when the measured overhead is acceptable

## Decision Table

| Situation | Default choice |
|---|---|
| Sparse irregular hot path | raw CUDA/C++ |
| Dense path already served by cuBLAS/cuBLASLt/cuSPARSE/NCCL | raw CUDA/C++ plus library interop |
| Regular loops with modest performance sensitivity | OpenACC or OpenMP target may be acceptable |
| C++ algorithmic code where developer speed matters more than absolute control | stdpar may be acceptable after measurement |

## Red Flags

- the model relies on hidden managed-memory movement
- irregular sparse work needs exact layout control
- the offload path prevents using the best CUDA library path cleanly
- the abstraction makes profiling and buffer ownership ambiguous

## Bad Uses

- accepting managed-memory overhead without measurement
- using stdpar or directive offload on a path that really needs precise sparse layout and data residency control
- replacing a known good library call with a prettier abstraction that adds movement or staging cost

## Baseline Rule

Before keeping an NVHPC abstraction on a hot path, compare it against:

1. raw CUDA/C++ plus direct library calls
2. end-to-end steady-state time
3. host-device movement behavior
4. profiler evidence, not just source-code simplicity
