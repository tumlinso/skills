# Launch-Bound Patterns

## When To Suspect Launch Overhead

Suspect launch-bound behavior when:

- Nsight Systems shows a train of short kernels with visible gaps
- kernel-level metrics look reasonable but end-to-end throughput is poor
- fusion or grouped variants produce larger gains than local kernel tweaks

## Typical Sources

- chains of pointwise kernels
- repeated tiny reductions
- repeated small cuBLAS calls that should be grouped or batched
- sparse glue pipelines that decompose every stage into a separate launch

## Best Levers

1. fuse adjacent kernels when they share data
2. use grouped or batched library calls
3. capture the steady-state loop with CUDA Graphs
4. pre-create descriptors and workspaces outside the hot path

## Launch Overhead Versus Divergence

Prefer moderate divergence over extra launches when:

- the branch bodies are short
- the split would add many tiny kernels
- the split would also add extra memory traffic

Prefer specialization over divergence when:

- each path is long and materially different
- each specialized kernel can use a better launch shape or tile
- the launch count stays modest after the split

Prefer binning or compaction over both when:

- stable workload classes repeat every step
- one general kernel would both diverge and overprovision resources

## CUDA Graph Rule

Graphs help when:

- the steady-state step repeats many times
- the launch graph is stable
- you already removed the most obvious fusion opportunities

Graphs do not rescue:

- a fundamentally memory-bound giant kernel
- a communication pattern that is wrong for the topology
- a badly over-fused divergent kernel whose real limit is spills or scheduler pain

## What To Measure

- total step time before and after
- GPU idle gap reduction
- number of launches in the steady-state step
- whether graph capture changed synchronization behavior
