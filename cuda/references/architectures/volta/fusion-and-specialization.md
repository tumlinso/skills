# Native V100 Fusion And Specialization

Use this route when the main question is whether a Volta-native path should stay
fused, split, or be specialized by work class.

Primary source:

- NVIDIA Volta Tuning Guide:
  https://docs.nvidia.com/cuda/volta-tuning-guide/

## V100 Bias

On native V100, aggressive fusion is often right when the alternative would add
extra HBM passes or launch trains. Volta does not have Ampere async copy or
Hopper TMA to rescue a decomposition that is fundamentally too fragmented.
On this machine, rereading and rewriting full tensors through HBM is often more
expensive than it first appears. CUDA Graph capture can reduce launch overhead,
but it does not erase the cost of extra HBM passes. Bias toward fusion first
when the real loss is repeated full-tensor traffic.

## Fuse When

- the same sparse or glue-heavy working set is touched repeatedly
- intermediate state can stay in registers or shared memory
- the alternative adds obvious global-memory round trips
- the alternative would reread or rewrite full tensors through HBM just to keep
  phases separate
- launch overhead is visible in the Nsight Systems timeline

## Split When

- ptxas shows enough register growth to force spills
- occupancy collapses so far that memory latency stops being hidden
- one branch or phase clearly belongs to a library boundary
- specialization by row bin, tile class, or feature density removes long
  divergent sequences

## Specialize When

- branch bodies are materially different
- memory access patterns diverge by work class
- one class is consistently heavier and can justify a separate kernel

## Do First

1. Measure whether the real loss is HBM passes or register pressure.
2. If the loss is repeated HBM traffic, prefer fusion before reaching for CUDA
   Graphs or other launch-side cleanup.
3. If fusion still looks right, keep one kernel per TU so the wider kernel stays
   inspectable.
4. If specialization looks right, split by the property that actually changes
   branch behavior or memory shape, not by cosmetic type boundaries.
