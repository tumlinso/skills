# E05 — Warp routing, matching and lookup

> When do register exchange and equality grouping beat memory-based structures?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
**Read when:** experiment, warp, routing, matching, and, lookup.
**Prerequisites:** R12. **Evidence:** S03 S08 S10.

**Question:** When do register exchange and equality grouping beat memory-based structures?

**Minimal setup:** Implement shuffle tables, match-group reservations and mask rank/select with explicit participation. Validate every small index/group shape first.

**Sweep:** Table size, query uniformity, key cardinality, active masks, payload width and reuse.

**Discriminating observation:** Break-even surfaces for register/shared/constant lookup and grouped atomics.

**Baseline:** Cached global/shared tables and one-atomic-per-lane plus established aggregation.

**Confounders / correctness:** Inactive source lanes, undefined selected values, multiword selection and hidden spills.

**Access gate:** Use valid synchronized primitives; do not use incidental activemask as logical membership.

**Related:** C03 C04 M02 M04 M05.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


## Measured coverage (2026-10-06)

The measured units were shuffle/cached-table lookup, per-lane/match-group atomics, and small-mask rank/select. Sixty-nine GPU cases passed at sizes 31/32/65, lookup table sizes 8/32, uniform/diverse query patterns, and aggregation cardinalities 2/8/16; each timing used one requested kernel iteration with repeated event samples. Lookup/atomic medians were generally 0.005120 ms, with variable p95 values; rank/select median/p95 were 0.006144/0.007168 ms. Rank/select produces ordinal indices and does not move arbitrary payloads. Implementation: [`run_e05`](../benchmarks/native/logic.cu#L588), [`run_rank_select`](../benchmarks/native/logic.cu#L545). [Measured summary](evidence/v100-20261006/E05.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: The tested lookup variants, aggregation outputs and software ordinal scan/rank/select pass correctness checks.
- Design implication (inference): Keep ordinal selection separate from payload movement when estimating a complete data path.
- Does not establish: A convincing performance winner, a native `__fns` payload operation, or bank-counter causality.
- Original protocol gaps: Broader table/query/reuse surfaces, multiword payload selection, complete payload movement, and stronger application-level aggregation baselines remain absent.
