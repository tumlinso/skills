# E23 — VMM alias and view behavior

> Can a legal view remove address work without hidden coherence or translation cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, vmm, alias, and, view, behavior.
**Prerequisites:** R12. **Evidence:** S18 S31.

**Question:** Can a legal view remove address work without hidden coherence or translation cost?

**Minimal setup:** Query granularity and permissions; construct isolated views with synchronized phase changes and a verified reference.

**Sweep:** View size, alias count, page footprint, window length and access phase.

**Discriminating observation:** Correct output plus mapping amortization and translation cost.

**Baseline:** Two-segment ring windows and simple modulo.

**Confounders / correctness:** Mapping success is not a complete concurrent-alias visibility contract. Do not remap live accesses.

**Access gate:** Public VMM supported by actual device/driver; no PTE edits.

**Related:** C29 M40 R08.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
