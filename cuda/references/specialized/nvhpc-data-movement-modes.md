# Data Movement Modes

## Why This Matters

On V100, hidden or poorly controlled movement can erase much of the value of the GPU. NVHPC memory modes are therefore not just correctness choices; they are performance choices.

## Separate Memory

Meaning:

- host and device memory remain distinct
- movement must be explicit through the programming model

Implication:

- best when you need exact control
- easiest model for peak-oriented CUDA/library code

## Managed Memory

Meaning:

- memory can be migrated automatically

Implication:

- simpler to use
- can add runtime overhead
- historically requires caution with what allocations are actually managed

For stdpar, NVIDIA’s documentation notes managed-memory mode can carry higher runtime allocator overhead, mitigated with pools.

## Unified Memory

Meaning:

- broader shared address-space behavior

Implication:

- fewer restrictions than managed mode
- still not a free pass for peak performance
- explicit data management can still matter for tuning

## Performance Rule

If the path is hot, sparse, irregular, or staging-sensitive:

- prefer explicit movement and ownership
- do not assume managed or unified memory is free
- measure page migration or implicit movement costs before accepting the abstraction
