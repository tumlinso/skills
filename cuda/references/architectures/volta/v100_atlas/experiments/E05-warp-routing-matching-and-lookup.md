# E05 — Warp routing, matching and lookup

> When do register exchange and equality grouping beat memory-based structures?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
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
