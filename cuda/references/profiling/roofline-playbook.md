# Roofline Playbook

## Memory-Bound Kernel

Signs:

- high DRAM throughput
- low relative SM throughput
- little sensitivity to more occupancy
- the achieved point sits in the memory-bound region of the roofline chart
- Memory Workload Analysis shows pressure on bandwidth or serialized memory behavior

Levers:

- improve coalescing
- reduce bytes moved
- fuse follow-on work
- keep intermediates in registers or shared memory when reuse is real
- shorten the full memory path rather than polishing arithmetic
- remove format conversions or packing passes from the hot path

Do not:

- chase occupancy in isolation
- add shared memory without proving it reduces real traffic
- spend time on arithmetic instruction tuning before bytes moved are reduced
- blame divergence first when the kernel is clearly pinned to a memory roofline

## Compute-Bound Dense Kernel

Signs:

- dense math is hot
- Tensor Core activity matters
- arithmetic intensity is high enough that memory is not the first wall
- the achieved point sits under the compute ceiling rather than the memory slope

Levers:

- align shapes to multiples of 8
- increase useful tile quality
- use CUTLASS or library kernels when they beat the handwritten path
- reduce register spills without collapsing the tile too far
- confirm the path is actually using Tensor Core-friendly math modes

Do not:

- keep awkward exact shapes if modest padding unlocks much better kernels
- hand-write WMMA just because the operation is matrix-shaped

## Register-Limited Kernel

Signs:

- low occupancy with high registers/thread
- spills or residency limits dominate
- small tile changes produce large shifts in active warps or local-memory traffic

Levers:

- shrink tiles or fusion depth
- test register-cap variants
- reduce live range pressure
- split obviously over-fused epilogues if they block residency

Experiments worth running:

- baseline
- smaller tile
- reduced unrolling
- capped-register build

## Launch-Bound Kernel

Signs:

- many tiny kernels
- timeline dominated by launch trains
- kernel-by-kernel optimization produces little end-to-end gain

Levers:

- fuse kernels
- batch work
- use CUDA Graph capture
- move repeated small library calls into grouped variants when possible
- compare against a moderately divergent fused path before splitting everything into more kernels

## Shared-Memory-Limited Kernel

Signs:

- heavy carveout
- occupancy falls sharply with shared-memory size
- bank-conflict or wavefront behavior looks poor in memory tables

Levers:

- confirm reuse is worth it
- compare against a lighter shared-memory design
- move warp-local exchange back to shuffle where possible
- reduce bank conflicts before increasing carveout further

## Counter Collection Order

For a serious tuning pass, look at:

1. roofline location
2. Memory Workload Analysis
3. Occupancy
4. Scheduler / warp-state behavior
5. Launch statistics

If those disagree, trust the end-to-end bottleneck first and the prettiest single metric last.
