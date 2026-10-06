# E03 — Cross-pipeline interference

> Can two useful operation families overlap without saturating another shared resource?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
**Read when:** experiment, cross-pipeline, interference.
**Prerequisites:** R12. **Evidence:** S01 S04 S35.

**Question:** Can two useful operation families overlap without saturating another shared resource?

**Minimal setup:** Time each family alone, serially combined and interleaved at equal semantic work. Preserve enough independent operands to expose overlap.

**Sweep:** INT/FP/tensor/conversion/load mixes; relative work ratios; live-register budget.

**Discriminating observation:** Combined critical time closer to a maximum than a sum only where genuine overlap exists; counters explain new bottlenecks.

**Baseline:** Best isolated and serial schedules, not an intentionally poor ordering.

**Confounders / correctness:** Shared issue, register ports, HBM and power; extra work invalidates the comparison.

**Access gate:** Public/PTX forms; no unsupported later-architecture instructions.

**Related:** C18 C19 M16 R14.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


## Measured coverage (2026-10-06)

The semantic work was equal-count uint32 adds and FP32 `fmaf`, with both outputs consumed; isolated integer, isolated FP, serial and interleaved forms were tested. Eight GPU cases passed at sizes 4,096/65,536 with 16/256 iterations and 30 event samples per case. At 65,536, serial and interleaved medians were 0.009216/0.008192 ms, with both p95 at 0.009216 ms. At 4,096, all four medians were 0.005120 ms; serial p95 was 0.019456 ms. Timing includes the complete kernel and loop control. Implementation: [`run_e03`](../benchmarks/native/logic.cu#L368), [`run_e03_steady`](../benchmarks/native/logic.cu#L268). [Measured summary](evidence/v100-20261006/E03.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: Equal-work schedule measurements for this integer-add/FP32-FMA pair; the larger case has a lower interleaved median than serial with equal p95.
- Design implication (inference): Matched-work schedule comparisons are useful for testing overlap hypotheses between operation families.
- Does not establish: A resource-causality explanation, a new model algebra, or overlap in a scientific workload.
- Original protocol gaps: Tensor/conversion/load combinations, work-ratio and live-register sweeps, counter-backed bottleneck explanation, and broader workload validation are absent.
