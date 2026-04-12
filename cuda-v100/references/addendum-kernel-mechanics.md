# Addendum: Kernel Mechanics

Use this addendum when the main question is not yet "how do I tune this hot kernel counter-by-counter?" but rather:

- should these kernels be fused?
- is this branch structure actually harmful?
- should I split this into specialized kernels instead of forcing one general kernel?
- is launch overhead worse than moderate divergence here?
- which CUDA memory tier should hold the critical intermediates on V100?

If the user explicitly asks for PTX-level guidance for branch shaping or sparse hot paths, route from here into `references/addendum-ptx-routing.md` only after the structural decision is already clear.

Use this before `references/addendum-kernel-roofline-lab.md` when the kernel structure itself is still unsettled.

## Quick Map

- `1. First Gate`
- `2. Fusion Rules`
- `3. Divergence Rules`
- `4. Launch Overhead Versus Divergence`
- `5. V100 Memory Tier Rules`
- `6. Profiler Cues`
- `7. Resume Rule`

## 1. First Gate

Before changing code, classify the dominant pain:

1. too many full-memory passes
2. too many tiny launches
3. long divergent regions inside one warp
4. register spills or shared-memory bloat from over-fusion
5. wrong memory-tier placement for the main intermediates

Do not jump into instruction tuning until one of those is clearly dominant.

## 2. Fusion Rules

### Prefer Fusion When

- adjacent kernels read and write the same full-sized tensors
- the fused path can keep intermediates in registers or shared memory
- the unfused path is launch-bound or memory-pass-bound
- the branch structure inside the fused kernel stays short or coherent
- the work is glue-heavy and not already well served by one library call

### Prefer Separate Kernels When

- the fused kernel would create long mutually exclusive heavy paths
- the fused kernel would materially increase register pressure or spills
- the fused kernel would need so much shared memory that occupancy collapses without real reuse
- each path wants a different launch shape, tile shape, or memory layout
- the split lets you specialize for stable workload classes such as short rows vs long rows

### Measure First When

- the saved launch count is small
- the saved memory traffic is unclear
- the fused kernel may become spill-heavy
- the current kernels are already large enough that launch cost may be secondary

### Anti-Patterns

- fusing unlike-shaped work just to reduce launch count
- over-fusing epilogues until local-memory traffic appears from spills
- replacing a clean grouped library path with a worse handwritten fused kernel

## 3. Divergence Rules

Warp divergence is not automatically bad. Treat it as a tradeoff.

### Divergence Is Usually Acceptable When

- the branch regions are short
- most lanes still follow the same path most of the time
- the branch prunes expensive work for inactive lanes
- the alternative would add extra full-memory passes or extra launches
- the branch is localized near the edge or tail of the problem

### Divergence Is Usually Harmful When

- each branch path is long and expensive
- the paths have materially different memory-access patterns
- the branch also destroys coalescing, reuse, or tile regularity
- the workload naturally separates into stable classes that could be binned
- the divergence persists through most of the hot steady-state loop

### Prefer Specialization Or Binning When

- one class is consistently short and another is consistently heavy
- sparse rows or tiles have persistent skew
- the same branch pattern repeats across many iterations
- the split would allow much better launch geometry or memory behavior

### Clarify What Does Not "Belong In CUDA"

- ordinary branching does belong in CUDA when it is the fastest full-path design
- divergence is a performance question, not a correctness or style violation
- moving branch-heavy work to the CPU is usually wrong if it creates host round-trips or breaks residency
- the real question is whether the branch should stay in one kernel, become multiple kernels, or be handled by preprocessing or compaction

## 4. Launch Overhead Versus Divergence

On V100, many tiny launches can lose badly to moderate divergence. But a giant over-fused divergent kernel can also lose.

### Prefer One Kernel With Moderate Divergence When

- each branch body is short
- the kernel train is currently the obvious end-to-end bottleneck
- the fused kernel removes extra HBM passes
- the current decomposition has visible GPU idle gaps between short kernels

### Prefer Multiple Specialized Kernels When

- the divergent paths are long or structurally different
- each specialized path can use a better launch shape or tile
- the split removes long serialized warp regions
- the launch count stays reasonable after specialization

### Prefer Binning Plus Specialization When

- the workload has recurring classes such as light vs heavy rows
- one general kernel would either diverge badly or overprovision resources
- the binning cost is smaller than the saved serialization and memory waste

### Prefer Graphs Or Grouped Launches When

- the main issue is repeated stable launch trains
- the decomposition is already otherwise sensible
- obvious fusion opportunities are already exhausted

### Practical Rule

- choose extra launches over divergence when the divergent regions are long and hot
- choose divergence over extra launches when the branches are short and the alternative is a launch-heavy, memory-pass-heavy decomposition
- choose neither naive fusion nor naive branching when the data naturally supports class-based specialization

## 5. V100 Memory Tier Rules

Think in terms of bytes moved and reuse earned.

### Registers

Use for:

- fused intermediates
- warp-local partials
- short-lived values with clear reuse

Warnings:

- over-fusion can turn register pressure into local-memory spill traffic
- lower occupancy is acceptable only if spills and stalls do not explode

### Shared Memory

Use for:

- cross-thread reuse
- staging tiles that truly reduce global traffic
- reductions or exchange that cross warp boundaries

Warnings:

- do not use it for warp-local exchange that shuffle already handles
- do not use it just because the problem "looks tiled"
- above 48 KB per block requires explicit opt-in and can materially reduce occupancy

### Global Memory / HBM

Assume:

- it is fast compared with PCIe
- it is still slow enough that repeated full passes dominate many kernels

Rules:

- pay for HBM traffic only when it buys real useful work
- fusion is often a memory-traffic decision before it is a launch decision

### L1 / L2-Backed Access

Use the cache hierarchy as a helper, not a plan.

Rules:

- improve access regularity first
- do not assume L1 or L2 will rescue scattered or divergent traffic
- if a shared-memory design does not clearly beat the cached path, prefer the simpler cached path

### Local Memory

Treat local memory as a warning sign unless you intentionally need large private arrays.

Rules:

- most hot local-memory traffic means register spills
- if local-memory traffic rises after fusion, the fusion depth may be wrong

### Constant Memory

Use when reads are:

- warp-uniform
- small
- read-mostly

Avoid when accesses vary heavily across lanes.

### Host / PCIe / NVLink

These are system-path memory choices, not kernel-local memory choices.

Rules:

- keep host transfers out of kernel mechanics decisions whenever possible
- do not accept a "cleaner" kernel decomposition that reintroduces host-visible staging or extra transfers

## 6. Profiler Cues

### Signs The Real Win Is Fusion

- Nsight Systems shows short-kernel trains with visible idle gaps
- Memory Workload Analysis says bytes moved dominate
- end-to-end time improves more from removing passes than from local arithmetic tuning

### Signs The Real Win Is Specialization

- Scheduler or warp-state behavior stays poor after obvious fusion
- one class of input is much heavier than another
- branch-heavy kernels remain hot even when launch count is already low

### Signs Divergence Is Not The Main Problem

- kernel is clearly memory-bound
- branch regions are short
- end-to-end wins come from reducing passes, not from removing branches

### Signs Over-Fusion Went Too Far

- registers/thread rises sharply
- local-memory traffic appears or grows
- occupancy collapses without a compensating throughput win
- shared-memory carveout becomes the new limiter

## 7. Resume Rule

Resume the main `cuda-v100` workflow when:

- the right decomposition is chosen
- the right memory tier for critical intermediates is clear
- the remaining question is now counter-driven hot-kernel tuning

Then move to `references/addendum-kernel-roofline-lab.md`.

## Support References

- Read `references/v100_programming_guide.md` for the system-level ordering and V100 memory-movement priorities.
- Read `references/v100_cuda_cpp_optimize.md` for concrete Volta kernel rules, shared-memory use, register-pressure handling, and CUDA Graph use.
- Read `references/roofline-launch-bound-patterns.md` when the choice is mainly fusion, grouping, or graphs.
- Read `references/roofline-counter-triage.md` when profiler output suggests over-fusion, register pressure, or scheduler pain.
- Read `references/roofline-playbook.md` when you need the limiter-to-lever map after the structure is already reasonable.

## Output Requirements

Be explicit about:

- whether the current loss comes from memory passes, launch count, divergence, or over-fusion
- whether divergence is actually harmful here or just present
- whether extra launches are preferable to the current divergent structure
- which memory tier should hold the critical intermediates
- what profiler evidence would confirm that the chosen tradeoff is right
