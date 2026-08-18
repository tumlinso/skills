# Volta Router

Assume **Tesla V100 16 GB, `sm_70`**, usually on the native 4xV100 host.

Use this route for native Volta behavior, V100-specific tuning, or `sm_70`
implementation questions.

Route narrowly. Read one row, then one micro-router, then one deep manual only
if still unresolved.

If benchmark or profiler summaries already exist, run
`scripts/common/recommend_cuda_route.py --arch volta ...` before opening more
docs.

Native topology:

- fast pair: `0 <-> 2`
- fast pair: `1 <-> 3`
- worst steady-state paths: `0 <-> 3`, `1 <-> 2`

Rules:

1. Prefer native Volta paths, not generic CUDA median doctrine.
2. Treat repeated HBM passes as a first-class loss.
3. Use summaries before raw reports.
4. Keep the build narrow to `sm_70`.

## Choose Your Path

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "make native V100 faster", "mixed glue-heavy path", "not sure which native loss dominates" | `references/architectures/volta/routes/native.md` | `references/architectures/volta/native-v100-extreme.md` |
| "fuse or split", "divergence vs launches", "specialize or bin", "graphs vs fusion" | `references/architectures/volta/routes/fusion.md` | `references/addendum-kernel-mechanics.md`, `references/roofline-launch-bound-patterns.md` |
| "one kernel is hot", "Nsight Compute limiter", "register pressure", "spills", "shared memory too high" | `references/architectures/volta/routes/hot-kernel.md` | `references/addendum-kernel-roofline-lab.md`, `references/architectures/volta/register-pressure-and-occupancy.md`, `references/v100_cuda_cpp_optimize.md` |
| "cuBLAS", "cuSPARSE", "cuDNN", "CUTLASS", "CUB", "NVIDIA library", "library or custom CUDA" | `references/common/compute-libraries.md` | `references/architectures/volta/routes/tensor.md`, `references/v100_cuda_cpp_optimize.md` |
| "Tensor Cores", "WMMA", "CUTLASS", "dense blocked custom op", "Tensor Cores not firing" | `references/architectures/volta/routes/tensor.md` | `references/addendum-tensor-core-routing.md`, `references/volta-tensor-core-low-level.md` |
| "PyTorch C++/CUDA op", "extension boundary", "custom op on V100" | `references/architectures/volta/routes/torch-op.md` | `references/addendum-torch-extensions.md`, `references/torch-extension-playbook.md` |
| "benchmark loop", "profile-build", "summary-first benchmarking", "standardize benchmarks" | `references/architectures/volta/routes/benchmark.md` | `references/architectures/volta/native-benchmark-loop.md`, `references/benchmark-standardization.md` |
| "it does not fit", "buffers exploded", "batch collapsed" | `references/addendum-memory-budgeting.md` | `references/memory-accounting.md`, `references/memory-fit-strategy.md`, `references/v100_programming_guide.md` |
| "GPU is idle", "HtoD dominates", "pipeline starving device" | `references/addendum-host-device-pipeline.md` | `references/pipeline-bottlenecks.md`, `references/pipeline-overlap-rules.md`, `references/v100_profiling_interpretation.md` |
| "DDP or NCCL is slow", "which ranks go where", "multi-GPU scaling is bad" | `references/addendum-ddp-topology.md` | `references/ddp-topology-playbook.md`, `references/v100_programming_guide.md` |
| "it crashes", "illegal memory access", "compute-sanitizer", "cuda-gdb" | `references/addendum-crash-debugging.md` | `references/compute-sanitizer-playbook.md`, `references/cuda-gdb-playbook.md`, `references/crash-signature-map.md` |
| "How do I port CPU-centric code to CUDA?" | `references/addendum-cpu-porting.md` | `references/cpu-porting-decision-tree.md`, `references/cpu-to-cuda-rewrite-patterns.md`, `references/cpu-porting-sparse-bio.md` |
| "I explicitly want PTX guidance", "show me PTX or SASS" | `references/addendum-ptx-routing.md` | `references/architectures/volta/sass-and-ptx-triage.md`, `references/ptx-volta-extreme.md` |
| "Should this use NVHPC, OpenACC, OpenMP target, or stdpar?" | `references/addendum-nvhpc-cpp.md` | `references/nvhpc-tradeoffs.md`, `references/v100_cuda_cpp_optimize.md` |
| "This is sparse omics or bio data" | `references/addendum-bio-data-layouts.md` | `references/v100_bioinformatics_guide.md` |
| "I need a general V100 path" | `references/architectures/volta/routes/native.md` | `references/v100_programming_guide.md` |

## Scripts

- `scripts/common/recommend_cuda_route.py`: map benchmark or profiler summaries to one next route
- `scripts/profile_nsys.sh`: timeline and setup summary
- `scripts/profile_ncu.sh`: hot-kernel counter summary
- `scripts/debug_crash.sh`, `scripts/debug_compute_sanitizer.sh`, `scripts/debug_cuda_gdb.sh`: crash triage
- `scripts/dump_ptx_hotspot.sh`, `scripts/split_cuda_translation_unit.py`: explicit PTX/SASS isolation
- `scripts/architectures/volta/emit_profile_build.py`, `scripts/architectures/volta/summarize_ptxas_verbose.py`, `scripts/architectures/volta/summarize_sass_hotspot.py`, `scripts/architectures/volta/gen_native_bench_matrix.py`: narrow Volta helpers

## Output

Be explicit about:

- whether the route assumed native V100 `sm_70`
- which micro-router owned the first decision
- whether benchmark, `nsys`, `ncu`, or dump evidence drove the call
- whether the path stays library-backed, fused custom CUDA, CUTLASS, WMMA, or another owner
- whether HBM traffic, launch trains, register pressure, Tensor routing, or topology dominated first
