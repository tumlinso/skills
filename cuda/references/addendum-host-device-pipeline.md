# Addendum: Host Device Pipeline

Use this addendum when the GPUs are waiting on the host, the batches are assembled poorly, or Nsight Systems shows gaps that are not explained by kernel runtime alone.

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

5. Resume the main `cuda` workflow if the issue becomes a device-side memcpy or kernel-level problem.

## Support References

- Read `references/pipeline-bottlenecks.md` for a host-side stall taxonomy.
- Read `references/pipeline-overlap-rules.md` for CPU-vs-GPU staging and overlap rules on V100 systems.

## Script

- Use `scripts/estimate_transfer_time.py` to estimate how expensive a host-to-device transfer pattern is relative to the available PCIe budget.

## Output Requirements

Be explicit about:

- where the stall is coming from
- what should move off the CPU if anything
- whether transfers are too fragmented
- what overlap or staging change should be tested next
