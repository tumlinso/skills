# Ampere Router

Assume **A100-class datacenter Ampere**, usually `sm_80`.

Use this route when the user names A100 or Ampere, or when the optimization
hinges on TF32, `cp.async`, async barriers, structured sparsity, or larger L2
behavior.

If benchmark or profiler summaries already exist, run
`scripts/common/recommend_cuda_route.py --arch ampere ...` before opening more
docs.

Primary sources:

- NVIDIA Ampere Tuning Guide:
  https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html
- cuSPARSELt docs:
  https://docs.nvidia.com/cuda/cusparselt/index.html

## Choose Your Path

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "it does not fit", "A100 buffers exploded", "which ranks go where", "multi-GPU scaling is bad" | `references/architectures/ampere/addendum-memory-topology.md` | `references/architectures/ampere/programming-guide.md` |
| "GPU is idle", "copies dominate", "input pipeline is starving A100" | `references/architectures/ampere/addendum-host-device-pipeline.md` | `references/architectures/ampere/profiling-interpretation.md` |
| "it crashes", "illegal memory access", "run compute-sanitizer" | `references/addendum-crash-debugging.md` | `references/compute-sanitizer-playbook.md`, `references/cuda-gdb-playbook.md` |
| "`cp.async`", "should I fuse or specialize", "Ampere kernel structure", "async staging" | `references/architectures/ampere/addendum-kernel-mechanics.md` | `references/architectures/ampere/programming-guide.md` |
| "one kernel is hot", "Nsight Compute limiter on A100" | `references/architectures/ampere/addendum-kernel-roofline-lab.md` | `references/architectures/ampere/profiling-interpretation.md` |
| "cuBLAS", "cuSPARSE", "cuSPARSELt", "cuDNN", "CUTLASS", "CUB", "NVIDIA library", "library or custom CUDA" | `references/common/compute-libraries.md` | `references/architectures/ampere/addendum-tensor-core-routing.md`, `references/architectures/ampere/programming-guide.md` |
| "TF32", "BF16", "Tensor Cores", "structured sparsity" | `references/architectures/ampere/addendum-tensor-core-routing.md` | `references/architectures/ampere/programming-guide.md` |
| "How do I port this CPU-centric code to CUDA?" | `references/addendum-cpu-porting.md` | `references/cpu-porting-decision-tree.md` |
| "I explicitly want PTX guidance" | `references/architectures/ampere/addendum-ptx-routing.md` | `references/ptx-general-guidelines.md` |
| "Should this use NVHPC, OpenACC, OpenMP target, or stdpar?" | `references/addendum-nvhpc-cpp.md` | `references/nvhpc-tradeoffs.md` |
| "Write or fix a PyTorch C++/CUDA op" | `references/addendum-torch-extensions.md` | `references/torch-extension-playbook.md` |
| "This is sparse omics / bio data" | `references/addendum-bio-data-layouts.md` | `references/v100_bioinformatics_guide.md` |
| "Standardize benchmarks" | `references/benchmark-standardization.md` | `references/architectures/ampere/profiling-interpretation.md` |
| "I need a general Ampere CUDA/C++ path" | `references/architectures/ampere/programming-guide.md` | `references/architectures/ampere/profiling-interpretation.md` |

## Opening Moves

1. Decide whether the workload really belongs on A100-specific paths.
2. Check whether the win is staging, Tensor Core routing, memory/topology, or
   kernel structure before changing code.
3. Keep the build narrow to `sm_80` while tuning.
