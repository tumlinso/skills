# Blackwell Router

Assume **B100 or B200-class Blackwell**, usually `sm_100`, with deployment
questions often tied to **GB200 NVL72**.

Use this route when the user names Blackwell, B100, B200, GB200, FP4, or
family-specific Blackwell build targets.

If benchmark or profiler summaries already exist, run
`scripts/common/recommend_cuda_route.py --arch blackwell ...` before opening
more docs.

Primary sources:

- https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html
- https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/

## Choose Your Path

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "it does not fit", "which ranks go where", "B200 scaling is bad", "GB200 collectives" | `references/architectures/blackwell/addendum-memory-topology.md` | `references/systems/gb200-nvl72.md`, `references/architectures/blackwell/programming-guide.md` |
| "GPU is idle", "copies dominate", "pipeline is starving B200" | `references/architectures/blackwell/addendum-host-device-pipeline.md` | `references/architectures/blackwell/profiling-interpretation.md` |
| "it crashes", "illegal memory access", "run compute-sanitizer" | `references/addendum-crash-debugging.md` | `references/compute-sanitizer-playbook.md`, `references/cuda-gdb-playbook.md` |
| "family-specific feature", "should I fuse or specialize", "Blackwell kernel structure" | `references/architectures/blackwell/addendum-kernel-mechanics.md` | `references/architectures/blackwell/programming-guide.md` |
| "one kernel is hot", "Nsight Compute limiter on B200" | `references/architectures/blackwell/addendum-kernel-roofline-lab.md` | `references/architectures/blackwell/profiling-interpretation.md` |
| "cuBLAS", "cuSPARSE", "cuDNN", "CUTLASS", "CUB", "NCCL", "NVSHMEM", "NVIDIA library", "library or custom CUDA" | `references/common/compute-libraries.md` | `references/architectures/blackwell/addendum-tensor-core-routing.md`, `references/architectures/blackwell/programming-guide.md` |
| "FP4", "microscaling", "Blackwell Tensor Cores" | `references/architectures/blackwell/addendum-tensor-core-routing.md` | `references/architectures/blackwell/programming-guide.md` |
| "How do I port this CPU-centric code to CUDA?" | `references/addendum-cpu-porting.md` | `references/cpu-porting-decision-tree.md` |
| "I explicitly want PTX guidance" | `references/architectures/blackwell/addendum-ptx-routing.md` | `references/ptx-general-guidelines.md` |
| "Should this use NVHPC, OpenACC, OpenMP target, or stdpar?" | `references/addendum-nvhpc-cpp.md` | `references/nvhpc-tradeoffs.md` |
| "Write or fix a PyTorch C++/CUDA op" | `references/addendum-torch-extensions.md` | `references/torch-extension-playbook.md` |
| "This is sparse omics / bio data" | `references/addendum-bio-data-layouts.md` | `references/v100_bioinformatics_guide.md` |
| "Standardize benchmarks" | `references/benchmark-standardization.md` | `references/systems/gb200-nvl72.md` |
| "I need a general Blackwell CUDA/C++ path" | `references/architectures/blackwell/programming-guide.md` | `references/architectures/blackwell/profiling-interpretation.md` |

## Opening Moves

1. Decide whether the optimization really needs Blackwell family-specific
   features.
2. Separate single-kernel questions from GB200 deployment topology.
3. Keep the build narrow to Blackwell while tuning.
