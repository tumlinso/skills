# Host And Device Pipeline

Use this guide when GPUs wait for the host, batch assembly is fragmented, or Nsight Systems shows gaps not explained by kernel runtime. For active capture or benchmark execution on the shared host, follow [host execution](../execution/host-execution.md) first; use controller admission and invoke capture/serialization wrappers only inside that admitted run.

## Workflow

1. Classify the stall.
   - data loading
   - parsing or preprocessing
   - sparse batch assembly
   - host-to-device transfer
   - synchronization or lack of overlap

2. Decide what belongs on CPU and what belongs on GPU.
   - keep CPU work only when it is cheaper than staging and transfer overhead
   - move preprocessing GPU-side when it can be fused into the steady-state path

3. Fix the staging path.
   - pinned memory for unavoidable transfers
   - batch small transfers
   - steady-state prefetching
   - NUMA-aware staging for the target GPU

4. Re-measure overlap and idle gaps.

5. If the gap is host-side, apply the [stall taxonomy](pipeline-bottlenecks.md); if the decision is CPU-versus-GPU staging or overlap, use [overlap rules](pipeline-overlap-rules.md). If Systems shows device-side copy engines or kernels dominate, move to profiling and device-kernel diagnosis.

## Script

- Use `scripts/estimate_transfer_time.py` to estimate how expensive a host-to-device transfer pattern is relative to the available PCIe budget.

## Report

Be explicit about:

- where the stall is coming from
- what should move off the CPU if anything
- whether transfers are too fragmented
- what overlap or staging change should be tested next
