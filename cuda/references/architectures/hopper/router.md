# Hopper Router

Assume **H100-class Hopper**, usually `sm_90`.

Use this route when the user names H100 or Hopper, or when the optimization
hinges on TMA, thread block clusters, distributed shared memory, FP8, or DPX.

If benchmark or profiler summaries already exist, run
`scripts/common/recommend_cuda_route.py --arch hopper ...` before opening more
docs.

Primary source:
https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html

## Choose Your Path

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "it does not fit", "which ranks go where", "H100 scaling is bad" | `references/architectures/hopper/addendum-memory-topology.md` | `references/architectures/hopper/programming-guide.md` |
| "GPU is idle", "copies dominate", "input pipeline is starving H100" | `references/architectures/hopper/addendum-host-device-pipeline.md` | `references/architectures/hopper/profiling-interpretation.md` |
| "it crashes", "illegal memory access", "run compute-sanitizer" | `references/addendum-crash-debugging.md` | `references/compute-sanitizer-playbook.md`, `references/cuda-gdb-playbook.md` |
| "TMA", "thread block clusters", "distributed shared memory", "should I fuse or specialize" | `references/architectures/hopper/addendum-kernel-mechanics.md` | `references/architectures/hopper/programming-guide.md` |
| "one kernel is hot", "Nsight Compute limiter on H100" | `references/architectures/hopper/addendum-kernel-roofline-lab.md` | `references/architectures/hopper/profiling-interpretation.md` |
| "cuBLAS", "cuSPARSE", "cuDNN", "CUTLASS", "CUB", "NCCL", "NVIDIA library", "library or custom CUDA" | `references/common/compute-libraries.md` | `references/architectures/hopper/addendum-tensor-core-routing.md`, `references/architectures/hopper/programming-guide.md` |
| "FP8", "Transformer Engine", "H100 Tensor Cores" | `references/architectures/hopper/addendum-tensor-core-routing.md` | `references/architectures/hopper/programming-guide.md` |
| "How do I port this CPU-centric code to CUDA?" | `references/addendum-cpu-porting.md` | `references/cpu-porting-decision-tree.md` |
| "I explicitly want PTX guidance" | `references/architectures/hopper/addendum-ptx-routing.md` | `references/ptx-general-guidelines.md` |
| "Should this use NVHPC, OpenACC, OpenMP target, or stdpar?" | `references/addendum-nvhpc-cpp.md` | `references/nvhpc-tradeoffs.md` |
| "Write or fix a PyTorch C++/CUDA op" | `references/addendum-torch-extensions.md` | `references/torch-extension-playbook.md` |
| "This is sparse omics / bio data" | `references/addendum-bio-data-layouts.md` | `references/v100_bioinformatics_guide.md` |
| "Standardize benchmarks" | `references/benchmark-standardization.md` | `references/architectures/hopper/profiling-interpretation.md` |
| "I need a general Hopper CUDA/C++ path" | `references/architectures/hopper/programming-guide.md` | `references/architectures/hopper/profiling-interpretation.md` |

## Opening Moves

1. Decide whether the win really requires TMA or clustered execution.
2. Decide whether FP8 or Transformer Engine routing is the real leverage.
3. Keep the build narrow to `sm_90` while tuning.
