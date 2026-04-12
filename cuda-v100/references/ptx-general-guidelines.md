# General PTX Guidelines For CUDA Workloads

Use this file when PTX guidance was explicitly requested, but the answer should stay reasonably portable while still being shaped for Tesla V100 and sparse irregular workloads.

This file is about when and how to use PTX, not about pretending PTX solves every performance problem.

## Quick Map

- `1. PTX Is A Last-Resort Tool`
- `2. Control-Flow Choices`
- `3. Predicate And Select Patterns`
- `4. Warp-Level Coordination Patterns`
- `5. Inline PTX Rules`
- `6. Algorithmic Choices Before PTX`
- `7. Anti-Patterns`

## 1. PTX Is A Last-Resort Tool

NVIDIA’s own guidance is consistent:

- PTX gives extra control
- inline PTX is available when needed
- hand-written PTX is an advanced technique
- portability and maintenance costs are real

That means:

- use libraries first when the mapping is clean
- use CUDA C++ plus good kernel structure before PTX
- use PTX only for narrow, repeated, stable hot sequences

## 2. Control-Flow Choices

PTX is useful for control flow when the problem is small enough that the exact instruction shape matters.

### Prefer Predication When

- the branch body is short
- the work skipped by the branch is modest
- the branch is hot and repeated
- the alternative branch structure is introducing avoidable divergence

Core PTX idea:

- compute a predicate with `setp`
- guard a short instruction sequence with `@p`

### Prefer Branchless Selection When

- you are choosing between small values or addresses
- the alternative branch is only there to pick one of two outcomes
- the selected path does not hide large memory-side effects

Useful PTX instructions:

- `setp`
- `selp`
- `slct`

### Prefer Real Branches Or Split Kernels When

- each side of the branch does meaningful work
- the memory-access patterns are structurally different
- the path naturally separates into stable workload classes
- the branch body is long enough that predicating everything wastes too much work

Volta independent thread scheduling does not make divergence free. It means warp-synchronous assumptions must be explicit and `_sync` intrinsics are mandatory when the warp cooperates.

## 3. Predicate And Select Patterns

Use PTX-level predicates for:

- threshold tests
- mask generation
- short edge guards
- cheap per-lane state changes

Use `selp` or `slct` for:

- small conditional moves
- branchless min/max-like selection when the compiler is not shaping it well
- choosing output indices, counters, or packed values without opening a full branch

Do not use predication to hide:

- long memory-heavy paths
- expensive gathers on one side and cheap work on the other
- large divergent loops that really want specialization

## 4. Warp-Level Coordination Patterns

For sparse and irregular work, PTX-adjacent warp patterns matter more than fancy arithmetic.

Look for:

- ballots to find active lanes
- warp masks to compact surviving work
- shuffle-based exchange for short reductions or prefix-like helpers
- match or vote-style coordination when keys or masks repeat within a warp

These patterns often beat lane-by-lane branching when:

- many lanes are inactive
- compaction is cheap
- the surviving work can be regrouped into a tighter path

Do not compact blindly. If compaction costs more than the skipped work, keep the simpler path.

## 5. Inline PTX Rules

Inline PTX is the preferred PTX surface for this skill.

Follow these rules:

- keep the PTX block narrow
- isolate the reason it exists
- constrain operands correctly
- mark blocks `volatile` only when required
- respect memory-space and side-effect semantics
- avoid namespace collisions in repeated inline snippets

Common failure modes from NVIDIA’s inline PTX guidance:

- incorrect constraints
- missing clobber or side-effect assumptions
- incorrect memory-space assumptions
- code that compiles but shapes registers or scheduling badly

Use inline PTX to improve a tiny sequence, not to turn the whole kernel into handwritten assembly.

## 6. Algorithmic Choices Before PTX

Before using PTX, ask:

- would binning rows or tiles remove more divergence
- would compaction remove more dead work
- would a split-kernel path be cleaner and faster
- would a format change reduce control-flow complexity
- would CUB, cuSPARSE, or CUTLASS solve the real problem better

For sparse or irregular kernels, the best gain is often:

- better binning
- better compaction
- better masks
- fewer passes

Only after those are stable should PTX decide the last few percent.

## 7. Anti-Patterns

- using PTX because the kernel is merely “complicated”
- predicating long heavy paths instead of splitting them
- replacing good library-backed paths with opaque inline PTX
- relying on old warp lockstep assumptions on Volta+
- letting inline PTX grow until the kernel becomes impossible to reason about

## 8. Official References

- PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
- Inline PTX Assembly Application Note: https://docs.nvidia.com/cuda/inline-ptx-assembly/
- CUDA C++ Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- CUDA C++ Best Practices Guide: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/
