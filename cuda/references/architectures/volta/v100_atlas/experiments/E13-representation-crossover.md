# E13 — Representation crossover

> How many uses repay bitplanes, packing or a changed numerical domain?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
**Read when:** experiment, representation, crossover.
**Prerequisites:** R12. **Evidence:** S08 S09 S03.

**Question:** How many uses repay bitplanes, packing or a changed numerical domain?

**Minimal setup:** Implement encoding, steady-state operators and decoding as separately timed stages plus a complete path.

**Sweep:** Reuse count, state cardinality, update rate, partial groups and data distribution.

**Discriminating observation:** A measured break-even model that predicts held-out cases.

**Baseline:** Best direct representation including existing packed or vectorized alternatives.

**Confounders / correctness:** Omitting maintenance or final decoding creates fictional wins; scalar versus packed output contracts differ.

**Access gate:** Run CPU identity checks first; inspect sm70 lowering for packed intrinsics.

**Related:** C00 C01 C02 C07 C08 C09 C37.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


## Measured coverage (2026-10-06)

The semantic unit was `u64(x)+u64(b)+carry`, with low 32 bits becoming next `x`, high 32 bits next carry, immutable `b`, and final `x`/carry materialized. The three GPU representations were native integer, 32 scalar instances per bitplane word, and a 512-entry nibble lookup. Nine cases covered random inputs at size/reuse 31/1, 1,024/8 and 65,536/64. At 65,536/64, resident median/p95 were 0.007168/0.007168 ms native, 0.119808/0.121856 ms bitplane, and 0.689152/0.697344 ms nibble. Full-path median/p95 were 0.468034/0.475263, 0.599238/0.607502 and 1.156385/1.173837 ms. Full path included H2D, resident compute and D2H/materialization; workspace allocation and host preparation were outside. Nibble table upload (0.01166 ms) was also excluded. Implementation: [`run_case`](../benchmarks/native/composition.cu#L260), [`run_composition`](../benchmarks/native/composition.cu#L456). [Measured summary](evidence/v100-20261006/E13.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: Native integer addition was the lowest measured complete path at all three tested size/reuse points; alternate representations also passed correctness.
- Design implication (inference): A Boolean or table encoding needs an amortization case that includes its conversion and output reconstruction costs.
- Does not establish: A universal native win, energy behavior, or results for other numerical domains, patterns and reuse regimes.
- Original protocol gaps: Broader size/pattern/reuse sweeps, workspace allocation cost, amortized table setup and alternative output contracts are missing.
