# Hopper Programming Guide

Use for overall H100-class strategy or when measured behavior points to Hopper
features. Assume `sm_90` unless the device and build target establish otherwise.

Primary source: [Hopper Tuning Guide](https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html).

## Family changes and baseline

- Tensor Memory Accelerator (TMA) changes the staging surface for large regular
  tensor movement.
- Thread block clusters and distributed shared memory change producer-consumer
  ownership; cluster only when inter-block locality pays for its coordination.
- FP8 opens additional Tensor Core routes when the numerical budget and software
  stack support them. DPX can help dynamic-programming-like patterns.
- Prefer an `sm_90`-only build while tuning. Revisit Ampere pipelines that exist
  only to work around copy overhead.

## Choose a direction from evidence

### Pipeline starvation

Prove starvation with Nsight Systems. Fix loader and staging trouble before
changing clustered kernels. Revisit TMA only after the device-side path is
representative.

### Kernel structure and staging

Use TMA for large regular movement, not irregular glue. Cluster only when blocks
truly cooperate on shared state. Avoid carrying Ampere staging complexity
forward when TMA or clusters provide a cleaner ownership model.

### Hot kernel

First confirm that the benchmark is representative. Check whether the limiter
is TMA setup, cluster synchronization, FP8 routing, or memory passes, then change
only the matching lever.

### Profiler interpretation

When reading Nsight output, ask whether TMA shifted the kernel away from copy
overhead, whether clusters reduced enough global traffic to matter, and whether
FP8 or Tensor Core routing actually fired. Classify the remaining limiter among
cluster synchronization, memory traffic, and occupancy before changing code.

### Memory fit and topology

Separate local memory-fit trouble from collective or topology trouble. Measure
the actual interconnect before fixing rank placement, and keep collective
experiments minimal until the topology hypothesis is clear. Larger memory does
not remove persistent activation or staging-buffer budgets. NVLink and NVSwitch
behavior depend on the machine, not the family name.

### Tensor Core routing

Route dense blocked math to Hopper-aware libraries when it maps cleanly. Use
FP8 or Transformer Engine only when the numerical budget and full software stack
permit it. Avoid this route for sparse, irregular, or memory-bound phases, or
when TMA and cluster structure matter more than raw math throughput.

### PTX

Read PTX only when explicitly requested and after isolating the hot path. First
decide whether TMA, cluster structure, or Tensor Core routing is still the real
issue; dump only the focused symbol for `sm_90`.
