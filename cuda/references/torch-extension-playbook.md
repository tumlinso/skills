# Torch Extension Playbook

Use this reference when writing PyTorch CUDA extensions for Tesla V100.

## Table of Contents

- Project registry
- Extension boundary
- Binding rules
- CUDA stream and device rules
- Backend choice
- Build rules for V100
- Forward and backward design
- Validation checklist

## Project Registry

Keep a repo-root `custom_torch_ops.md` as the living registry for nontrivial custom ops.

Bootstrap rule:

- detect repo root with `git rev-parse --show-toplevel 2>/dev/null || pwd`
- if `<repo_root>/custom_torch_ops.md` does not exist, create it from `assets/custom_torch_ops.template.md`
- add an entry before implementation when the op is still proposed
- update the same entry as the op moves through implementation and validation

Every registered op should capture:

- op name and purpose
- owning model or component
- Python, C++, and CUDA boundary
- input and output contract
- dtype, layout, and device assumptions
- backend choice: Tensor Core-capable library-backed, Tensor Core-capable
  custom CUDA, or regular custom CUDA
- backward or autograd notes
- distributed implications
- implementation status and code location

## Extension Boundary

Prefer one extension op per real fused unit of work.

Good reasons to create a custom op:

- many small pointwise or reduction kernels can be fused
- a sparse workflow is irregular enough that library composition adds extra memory passes
- the op must interleave custom logic with a library call

Bad reasons to create a custom op:

- wrapping a library GEMM with an inferior handwritten kernel
- moving easy tensor reshapes into opaque CUDA code
- hiding host-side copies or format conversions that should be explicit

On Volta, treat Tensor Core eligibility as the first backend question for a
custom op. If the op owns stable blocked or fused matrix math, prefer a Tensor
Core-capable implementation over a regular FP kernel even when that means
owning the kernel earlier than you would on newer families.

Before proceeding, register the op in `custom_torch_ops.md` unless it is a tiny local experiment that will not persist in the project.

## Binding Rules

At the C++ boundary:

- check `tensor.is_cuda()`
- check dtype explicitly
- check shape invariants explicitly
- check contiguity or required stride pattern explicitly
- make device transfers and contiguous copies opt-in and visible

Prefer a thin binding layer:

- parse arguments
- validate invariants
- choose the backend
- launch the CUDA or library path

Do not bury layout repairs inside the hot path unless the copy is a conscious tradeoff.

## CUDA Stream And Device Rules

Use the current PyTorch CUDA stream, not an unrelated default stream.

Required patterns:

- guard the target device before launching work
- obtain the current stream from the active device context
- pass that stream into raw CUDA launches and library handles

Typical pieces:

- `at::cuda::CUDAGuard`
- `at::cuda::getDefaultCUDAStream()` or the active current-stream accessor used by the project
- `C10_CUDA_KERNEL_LAUNCH_CHECK()` after kernel launches when appropriate

Do not assume stream 0 semantics if the training loop is already using non-default streams.

## Backend Choice

Inside an extension, prefer the same backend choices as the main V100 skill:

- check Tensor Core eligibility first for dense or blocked math
- cuBLAS or cuBLASLt for dense math when the op is still mostly a clean library
  mapping
- cuSPARSE for sparse primitives
- CUB for scans, reductions, and selection building blocks
- NCCL only when the extension is part of a real multi-GPU communication path

For Tensor Core-eligible custom ops on Volta:

- use a Tensor Core-capable library path first when it already expresses the op
  cleanly
- escalate earlier than on newer architectures to CUTLASS or an owned WMMA
  kernel when the op exists to preserve fused tile math, blocked layout
  ownership, or repeated epilogue or packing control
- do not keep the op as a thin wrapper around many library launches if that
  defeats the purpose of owning the extension boundary

For Tensor Core-eligible custom ops on any newer architecture:

- keep the owned custom-kernel option available when fusion, blocked layout
  control, or repeated library glue makes the library boundary the real limit
- do not reject a custom kernel just because a Tensor Core-capable library path
  exists in principle

Write custom CUDA kernels when:

- fusion removes meaningful HBM traffic
- the workload is irregular and library composition fragments execution
- the op is mostly glue and layout-aware bookkeeping
- the op has a stable Tensor Core-friendly inner loop and Volta-specific custom
  ownership is the real win

## Build Rules For V100

Compile specifically for Volta:

- target `sm_70`
- keep the toolchain compatible with the installed PyTorch CUDA build
- avoid assuming CUDA features that are unavailable or slower on V100

Build guidance:

- pass `-gencode arch=compute_70,code=sm_70` for native V100 builds
- include a PTX fallback only when distribution requirements justify it
- enable optimization flags appropriate to the project build, typically `-O3`
- keep debug and release settings explicit so profiling builds are reproducible

Do not optimize for Ampere-era behavior:

- no TF32 assumptions
- no BF16 Tensor Core fast-path assumptions
- no `cp.async`

## Forward And Backward Design

For forward:

- start from the true hot path
- keep temporaries minimal
- make layout assumptions explicit

For backward:

- reuse library primitives when they are already near-optimal
- fuse custom gradient logic only when composition adds material memory traffic or launch overhead
- avoid saving oversized intermediates if recomputation is cheaper on V100

If autograd state is large, cross-check with `references/addendum-memory-budgeting.md`.

## Validation Checklist

Before claiming the extension is correct and fast, verify:

- tensors stay on the intended device
- stream usage matches the surrounding PyTorch runtime
- no hidden contiguous copy dominates runtime
- the backend choice is justified against the best Tensor Core-capable library
  alternative and, on Volta, against earlier owned-kernel options when the op
  is meant to stay custom
- launch geometry is plausible for V100
- profiler evidence supports the claimed bottleneck
- `custom_torch_ops.md` reflects the current status, assumptions, and code location

If the hot kernel is still unclear, switch to `references/addendum-kernel-roofline-lab.md`.
