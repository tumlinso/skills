# NVHPC And Directive Offload

Use this guide when choosing NVC++ CUDA interop, OpenACC, OpenMP target, or stdpar for a performance-sensitive GPU path. The comparison is framed around the native V100 system; verify target compiler/toolkit support and architecture behavior on other systems.

Do not use compile success as performance evidence. For a broader CPU-to-GPU endpoint decision, start with [CPU porting](../workloads/cpu-porting.md); come here once offload is a serious candidate. Before active GPU benchmarks or profiles on the shared host, read [host execution](../execution/host-execution.md); use its controller admission, then invoke profiling wrappers within the admitted run.

## Decision

1. Identify the abstraction being considered.
   - NVC++ with CUDA interop
   - OpenACC
   - OpenMP target
   - stdpar

2. Check the overhead surface.
   - hidden data movement
   - managed or unified memory behavior
   - loss of explicit layout control
   - inability to fuse the real hot path

3. Prefer the lowest-overhead viable path.
   - raw CUDA/C++ and direct library calls when absolute control matters
   - NVHPC surface only when it improves implementation speed without losing too much control

4. Keep library interop explicit.
   - cuBLAS
   - cuSPARSE
   - NCCL
   - NVTX for profiling ranges

For a concrete comparison, use [performance tradeoffs](nvhpc-tradeoffs.md); when the choice hinges on data residency, use [offload models](nvhpc-offload-models.md) and [data movement](nvhpc-data-movement-modes.md); for explicit cuBLAS/cuSPARSE/NCCL/NVTX boundaries, use [library interop](nvhpc-library-interop.md). [Case notes](nvhpc-case-notes.md) help judge whether a proposed abstraction's measured overhead is acceptable.

## Script

- Use `scripts/emit_nvhpc_build_flags.py` to emit baseline compile commands for common NVHPC modes.

## Report

Be explicit about:

- which NVHPC surface is under consideration
- what overhead it may introduce
- whether raw CUDA/C++ remains the better answer
- what must be benchmarked before accepting the abstraction
