# Native CUDA Rewrite Patterns For CPU-Centric Code

Use this file when the endpoint is native CUDA or a mixed strategy with explicit CUDA on the hot path.

This file is about structural rewrite, not about CUDA syntax.

## Quick Map

- `1. Rewrite The Work Unit`
- `2. Rewrite The Data Layout`
- `3. Rewrite The Pipeline`
- `4. Replace CPU Primitives`
- `5. Decide What Stays On CPU`

## 1. Rewrite The Work Unit

Do not map CPU thread counts or task objects directly onto the GPU.

Instead:

- identify the real parallel unit in the data
- choose whether work is row-wise, tile-wise, element-wise, block-wise, or reduction-shaped
- decide whether one kernel, a small kernel train, or an explicit library call owns the phase

Good rewrite:

- CPU loop nest over rows -> row-parallel kernel or row bins
- CPU task queue of tiny callbacks -> grouped or fused GPU work
- serial stage chain -> device-resident staged pipeline

Bad rewrite:

- one GPU thread per former CPU task object when the tasks are tiny or irregular

## 2. Rewrite The Data Layout

CPU-friendly layout is often wrong for CUDA.

Common rewrites:

- AoS -> SoA or packed structure-of-arrays
- pointer-rich trees or object graphs -> flat arrays plus indices
- scattered metadata -> compact side arrays
- cache-line-friendly CPU blocking -> GPU tile blocking or explicit sparse format choices

Pick the layout that matches the dominant GPU phase, not the original CPU ownership model.

## 3. Rewrite The Pipeline

CPU code often alternates many small stages with host-visible state.

On GPU:

- keep data resident
- remove host round-trips
- separate setup from steady state
- fuse when it removes full-memory passes or tiny launch trains
- split when stable classes want different kernels or launch shapes

## 4. Replace CPU Primitives

Typical replacements:

- serial reduction -> shuffle/shared-memory reduction or library reduction
- serial filtering -> predicate plus compaction
- serial prefix logic -> scan
- repeated binary operations -> grouped library calls or fused kernels
- CPU sparse loops -> explicit sparse formats plus SpMM/SpMV or custom kernels for glue

Always ask whether CUB, cuSPARSE, cuBLAS, or cuBLASLt should own the rewritten primitive.

## 5. Decide What Stays On CPU

Keep work on CPU when:

- the phase is tiny
- the transfer and launch overhead dominate
- the phase is truly control-heavy and not repeated enough to matter

Move work to GPU when:

- the data is already resident
- the phase repeats heavily
- the GPU path can remove host-visible staging
- the phase becomes library-shaped or cleanly data-parallel after rewrite

## 6. Anti-Patterns

- preserving a CPU object model in the kernel boundary
- porting a serial loop literally and then trying to tune branch divergence
- optimizing kernel code before rewriting layout and decomposition
- treating host staging as unavoidable because the original CPU code did it that way
