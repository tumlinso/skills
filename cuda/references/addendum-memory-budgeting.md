# Addendum: Memory Budgeting

Use this addendum before tuning kernels when the job does not fit cleanly into 16 GB V100s or when throughput is being limited by conservative batch sizes, oversized buffers, or wasteful activation retention.

## Workflow

1. Build the memory budget.
   - parameters
   - gradients
   - optimizer state
   - activations
   - communication buffers
   - sparse intermediates and staging buffers

2. Classify the pressure.
   - static footprint too large
   - activations dominate
   - sparse staging dominates
   - communication or workspace buffers dominate

3. Apply the fit strategy in order.
   - remove avoidable buffers
   - checkpoint or recompute selected regions
   - change batch size and accumulation
   - change staging boundaries or sparse-to-dense boundary
   - reduce optimizer state pressure if necessary

4. Re-check throughput.
   - do not accept a fit strategy that destroys steady-state throughput without comparing alternatives

5. Resume the main `cuda` workflow when the issue becomes CUDA kernel, NCCL, or layout tuning.

## Support References

- Read `references/memory-accounting.md` for explicit budget categories and rough formulas.
- Read `references/memory-fit-strategy.md` for the order in which to trade memory for throughput on V100 16 GB.
- Read `references/memory-scenario-formulas.md` for concrete training-budget scenarios and throughput-preserving fit patterns.

## Script

- Use `scripts/estimate_v100_training_memory.py` to estimate rough training memory from parameter, activation, and optimizer assumptions.

## Output Requirements

Be explicit about:

- which category dominates memory
- which fit strategy is being chosen
- what throughput risk that strategy introduces
- what should be verified next with measurement
