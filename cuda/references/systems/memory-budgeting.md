# GPU Memory Budgeting

Use this guide before kernel tuning when the workload does not fit or batch size, oversized buffers, or retained intermediates limit throughput. The examples and 16 GB constraints below describe the native V100 system; recalculate against the selected GPU's actual capacity.

## Account, classify, and fit

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

5. Re-measure once it fits. For CUDA correctness/benchmark/profile execution on the shared host, first follow [host execution](../execution/host-execution.md); keep throughput measurement separate from profiled NCU timing.

Use [memory accounting](memory-accounting.md) when a category estimate or rough formula is missing. Use [fit strategy](memory-fit-strategy.md) to choose the order of buffer lifetime, checkpointing, batch/accumulation, sparsity-boundary, and optimizer changes. Use [scenario patterns](memory-scenario-formulas.md) when activations, sparse staging, optimizer state, or communication buffers clearly dominate.

## Script

- Use `scripts/estimate_v100_training_memory.py` to estimate rough training memory from parameter, activation, and optimizer assumptions.

## Report

Be explicit about:

- which category dominates memory
- which fit strategy is being chosen
- what throughput risk that strategy introduces
- what should be verified next with measurement
