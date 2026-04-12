# Volta-Extreme PTX For Tesla V100 `sm_70`

Use this file only when PTX guidance was explicitly requested and the user wants the deepest Volta-specific path.

Assume throughout:

- Tesla V100 16 GB
- native Volta `sm_70`
- CUDA 12.x-era toolchain and docs

This file is for extremely hot, stable kernels where instruction shape and control flow are already the right level to optimize.

## Quick Map

- `1. Volta Control-Flow Reality`
- `2. Predication Versus Branching`
- `3. Register And Scheduler Tradeoffs`
- `4. Warp-Shaped Sparse Patterns`
- `5. Inline PTX On Volta`
- `6. When Not To Do This`

## 1. Volta Control-Flow Reality

Volta adds independent thread scheduling, but it does not remove the cost of poor control flow.

Treat this as meaning:

- you must use `_sync` warp intrinsics explicitly
- old warp lockstep assumptions are unsafe
- predication and branch shape still matter
- splitting work by stable classes can still beat one overly general kernel

Volta-specific PTX work is most justified when:

- the branch structure is already tiny and hot
- the compiler keeps producing a worse shape than the kernel needs
- the sparse hot path is dominated by masks, thresholds, or lane-local decisions

## 2. Predication Versus Branching

Prefer predication on Volta when:

- the branch body is short
- the guarded instructions are cheap
- the branch is mostly about updating state, choosing a value, or issuing a small memory-side effect
- the alternative branch opens a long hot divergent region

Prefer a real branch or specialization when:

- one path is much heavier than the other
- memory access differs materially between paths
- the branch encloses loops or long pointer-chasing logic
- the workload can be binned into stable classes

Useful PTX surfaces for this:

- `setp`
- guarded instructions `@p`
- `selp`
- `slct`
- warp vote or mask patterns that reduce branch fan-out

## 3. Register And Scheduler Tradeoffs

On V100, PTX-level cleanup can still lose if it:

- lengthens live ranges
- raises registers per thread enough to crush residency
- introduces extra temporaries that spill
- makes the scheduler juggle too many partially active paths

That means:

- keep PTX sequences short
- benchmark after every structural change
- inspect register count and local-memory traffic after “branchless” rewrites
- reject a predicated rewrite if it raises spills or shrinks useful occupancy enough to erase the gain

## 4. Warp-Shaped Sparse Patterns

This is where Volta-specific PTX can be genuinely useful outside dense Tensor Core work.

Good candidates:

- row-skew dispatch inside a bin
- threshold and filter kernels with many inactive lanes
- compaction helpers for sparse writeout
- irregular segmented work where ballots and masks can tighten the active set
- tiny per-lane metadata transforms repeated across huge sparse datasets

Prefer PTX-level branch shaping when:

- each lane does only a small amount of work
- the branch pattern repeats heavily
- the alternative is a sea of short divergent branches

Prefer binning or split kernels when:

- heavy and light rows are obviously separable
- one path remains much larger than the other
- the work naturally wants different launch geometry

## 5. Inline PTX On Volta

Keep the inline PTX surface narrow:

- one micro-primitive
- one documented reason
- one benchmark that justifies it

Good uses:

- branchless select on hot metadata
- predicate-driven updates
- fixed short sequences where the compiler keeps emitting a worse branch shape

Bad uses:

- large multi-basic-block inline PTX regions
- replacing normal CUDA control flow before profiling proves it matters
- architecture-specific PTX embedded across the codebase without isolation

## 6. When Not To Do This

Do not use Volta-specific PTX when:

- the hot path is still memory-bound from too many passes
- the kernel still wants better sparse layout or binning
- the path is better expressed by CUB, cuSPARSE, or a split-kernel design
- the gain only appears in a toy microbenchmark

## 7. Official References

- Volta Tuning Guide: https://docs.nvidia.com/cuda/volta-tuning-guide/
- PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
- Inline PTX Assembly Application Note: https://docs.nvidia.com/cuda/inline-ptx-assembly/
- CUDA C++ Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
