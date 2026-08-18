# NVIDIA Compute Library Routing

Use this reference when the first real CUDA decision is whether the hot path
belongs to an NVIDIA library, a library-like template stack, or owned CUDA.

This file is a chooser, not a catalog. Pick the strongest primitive that owns
the hot region cleanly, then only move to custom CUDA when library composition
creates measurable extra launches, HBM passes, packing, or layout restrictions.
If the operation must run inside your own kernel, route to MathDx or
kernel-building-block libraries instead of host-launched library APIs.

Primary sources:

- CUDA Libraries: https://docs.nvidia.com/cuda-libraries/
- CUDA-X Libraries: https://developer.nvidia.com/cuda/cuda-x-libraries
- cuBLAS: https://docs.nvidia.com/cuda/cublas/
- cuSPARSE: https://docs.nvidia.com/cuda/cusparse/
- cuFFT: https://docs.nvidia.com/cuda/cufft/
- cuDNN Frontend: https://docs.nvidia.com/deeplearning/cudnn/frontend/latest/index.html
- MathDx: https://docs.nvidia.com/cuda/mathdx/
- cuBLASDx: https://docs.nvidia.com/cuda/cublasdx/
- cuFFTDx: https://docs.nvidia.com/cuda/cufftdx/
- cuSolverDx: https://docs.nvidia.com/cuda/cusolverdx/
- cuRANDDx: https://docs.nvidia.com/cuda/curanddx/
- nvCOMPDx: https://docs.nvidia.com/cuda/nvcompdx/
- CCCL, CUB, and Thrust: https://nvidia.github.io/cccl/
- CUTLASS: https://github.com/NVIDIA/cutlass
- NCCL: https://docs.nvidia.com/deeplearning/nccl/user-guide/docs/index.html
- NVSHMEM: https://docs.nvidia.com/nvshmem/api/

## Default Ladder

1. Use the standard library primitive when the operation maps directly.
2. Use planned, grouped, batched, or descriptor-driven variants before launching
   many tiny independent calls.
3. Use MathDx when the primitive must execute inside a CUDA kernel and fusion
   avoids global-memory round trips or launch boundaries.
4. Use CUTLASS, CUB, Thrust, or CCCL when the operation is still a known CUDA
   primitive but needs more ownership than a black-box library call exposes.
5. Use custom CUDA when fusion, data layout, persistent residency, or irregular
   control flow is the reason the library boundary loses.
6. Use PTX or SASS only after the library and custom-kernel ownership decision
   is already settled and the hot path is isolated.

Do not replace a strong library path with handwritten CUDA just because the
kernel is visible. Beat the library on the same shapes, data layout, streams,
and end-to-end boundary before owning the code.

## Library Decision Table

| Workload shape | Start with | Escalate when |
| --- | --- | --- |
| Dense GEMM, batched GEMM, grouped projections, dense linear algebra kernels | `cuBLAS` | epilogues, algorithm selection, or workspace choice matter |
| GEMM plus bias, activation, layout transforms, algorithm search, or mixed precision policy | `cuBLASLt` | the epilogue or packing cannot be expressed without extra passes |
| Sparse SpMV, SpMM, SpGEMM, SDDMM, sparse format conversion, sampled dense-dense math | `cuSPARSE` | irregular glue, fused preprocessing, or sparse metadata ownership dominates |
| Ampere-style 2:4 structured sparse matmul | `cuSPARSELt` | the sparsity pattern or fused work does not fit the library contract |
| Dense factorizations, eigensolvers, SVD, QR, dense linear solves | `cuSOLVER` | the solve is part of a larger fused or custom iterative method |
| Sparse direct solves | `cuDSS` | solver setup, ordering, or factor reuse does not fit the problem boundary |
| FFTs and convolution-through-FFT paths | `cuFFT` | a single kernel can fuse surrounding work enough to avoid extra traffic |
| Multi-GPU FFTs | `cuFFTMp` | decomposition or communication pattern is outside the library model |
| Device-side FFT fragments inside custom kernels | `cuFFTDx` | the operation is not actually FFT-shaped after fusion |
| Random number generation | `cuRAND` | the generator state or distribution must be fused into a larger kernel |
| Tensor contractions, tensor reductions, high-rank dense contractions | `cuTENSOR` | the contraction is small, irregular, or dominated by adjacent layout work |
| DNN primitives, fused operation graphs, convolutions, attention-like DNN blocks | `cuDNN` | the op boundary is not a stable DNN primitive or graph |
| Tiled GEMM, convolution, epilogue-heavy math that needs source ownership | `CUTLASS` | CUTLASS cannot express the tile shape, epilogue, or schedule cleanly |
| Reductions, scans, sorts, selection, histograms, block or warp collectives | `CUB` or CCCL primitives | the primitive must fuse with application-specific memory traffic |
| C++ algorithm-style GPU code, transforms, zip iterators, high-level scans or sorts | `Thrust` | abstraction overhead hides launch count, allocation, or layout costs |
| Multi-GPU collectives and point-to-point communication | `NCCL` | collectives must be embedded in a non-collective communication model |
| One-sided, PGAS, or GPU-initiated multi-GPU communication | `NVSHMEM` | ordinary collectives or host-orchestrated P2P already fit |
| Image, video, JPEG, or signal-processing primitives | `NPP`, `nvJPEG`, `nvCOMP`, or domain libraries | the project is not actually media or codec bound |

## Device-Callable And In-Kernel Libraries

Use MathDx when the operation needs to be embedded in your own CUDA kernel
rather than launched as a complete host-side library operation.

| In-kernel need | Start with | Notes |
| --- | --- | --- |
| GEMM or small dense matrix multiply inside a fused kernel | `cuBLASDx` | selected BLAS functionality, currently centered on GEMM |
| FFT fragments inside a custom kernel | `cuFFTDx` | avoids staging data out to a separate cuFFT launch |
| Dense factorization, solve, eigen, SVD, or least-squares work inside a kernel | `cuSolverDx` | use for supported batched or small dense solver-shaped work |
| Random number generation inside a kernel | `cuRANDDx` | prefer over older cuRAND device APIs for new in-kernel RNG work |
| Compression or decompression inside device code | `nvCOMPDx` | use when compression belongs in the fused device pipeline |
| Warp or block collectives, reductions, scans, sorting helpers | `CUB` or CCCL primitives | use inside owned kernels when the primitive is local to a block, warp, or cooperative group |
| Tiled GEMM or convolution kernel ownership | `CUTLASS` | use when the whole kernel shape is matrix-like and needs source-level control |

Keep all MathDx device-extension libraries from the same MathDx release when
combining them in one project. Treat them as in-kernel building blocks, not as
drop-in replacements for every host-launched library call.

Do not route to MathDx when the cleanest boundary is still one large library
operation. Prefer host-launched cuBLAS, cuFFT, cuSOLVER, cuRAND, or cuDNN when
the full operation already owns the data movement and launch boundary well.

## Architecture Caveats

- Volta V100: use library baselines for Tensor Core eligibility, but move
  earlier to CUTLASS, WMMA, or owned kernels when a stable custom op needs tile
  ownership, fixed blocked layout, or fewer HBM passes.
- Ampere A100: check TF32, BF16, `cuBLASLt`, and `cuSPARSELt` before writing a
  regular FP32 or sparse custom kernel.
- Hopper H100: keep FP8, Transformer Engine, TMA-friendly library paths, and
  Hopper-aware CUTLASS kernels in the baseline before owning dense math.
- Blackwell B100/B200: check FP4, microscaling, family-specific library support,
  and GB200 communication topology before assuming a custom kernel or custom
  collective is the right owner.

## Profiling Rules

- If a library call dominates and throughput is strong, tune descriptors,
  workspace, batching, streams, and layout before replacing it.
- If many small library calls dominate the timeline, first try grouped or
  batched APIs and CUDA Graphs. Fuse only when grouping does not remove the
  launch train or extra HBM passes.
- If a library path is fast locally but weak end-to-end, profile surrounding
  packing, format conversion, host staging, and synchronization.
- If a custom kernel appears faster than a library microbenchmark but loses
  end-to-end, keep the library path and fix the boundary.

## Output Requirements

When routing through this reference, state:

- the selected library or template stack
- why the workload maps to it
- whether the path is Tensor Core-capable library-backed, library-backed
  regular CUDA, CUTLASS or CUB-backed, or owned custom CUDA
- what data layout, dtype, batching, grouping, or workspace choice is required
- why custom CUDA is not justified yet, or what measured library-boundary cost
  justifies it
- which profiler evidence is needed next: `nsys` timeline, `ncu` hot-kernel
  counters, benchmark sweep, or topology/collective measurement
