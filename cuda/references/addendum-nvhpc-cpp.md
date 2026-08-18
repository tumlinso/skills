# Addendum: NVHPC C++

Use this addendum when the question is not "can NVHPC compile this?" but "does using NVHPC improve or hurt my V100 throughput relative to raw CUDA/C++ plus libraries?"

If the broader problem is how to port CPU-centric code efficiently to GPU, read `references/addendum-cpu-porting.md` first and come here only after offload is one of the serious candidate endpoints.

## Workflow

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

5. Resume the main `cuda` workflow if the issue becomes a standard Volta CUDA optimization problem.

## Support References

- Read `references/nvhpc-tradeoffs.md` for the performance-first decision rules.
- Read `references/nvhpc-offload-models.md` for the main NVHPC offload models and the kinds of overhead each can introduce.
- Read `references/nvhpc-data-movement-modes.md` for separate, managed, and unified memory consequences on V100-class workflows.
- Read `references/nvhpc-library-interop.md` for how to keep cuBLAS, cuSPARSE, NCCL, and NVTX explicit when using NVHPC surfaces.
- Read `references/nvhpc-case-notes.md` for concrete examples of when an NVHPC abstraction is acceptable and when it should be rejected on performance grounds.

## Script

- Use `scripts/emit_nvhpc_build_flags.py` to emit baseline compile commands for common NVHPC modes.

## Output Requirements

Be explicit about:

- which NVHPC surface is under consideration
- what overhead it may introduce
- whether raw CUDA/C++ remains the better answer
- what must be benchmarked before accepting the abstraction
