# E15 — Publication and progress litmus

> Can the proposed bounded protocol violate payload or scheduling invariants?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, publication, and, progress, litmus.
**Prerequisites:** R12. **Evidence:** S17 S25 S30 S33.

**Question:** Can the proposed bounded protocol violate payload or scheduling invariants?

**Minimal setup:** First write a memory-model/progress proof. Then run finite epoch-tagged producer/consumer tests with protected termination and adversarial delays.

**Sweep:** Grid admission, stream ordering, queue fullness, counter wrap bounds and device/host placement.

**Discriminating observation:** Any stale payload, reused slot or blocked producer falsifies the implementation; no observed failures do not prove legality.

**Baseline:** A supported explicit phase/event protocol.

**Confounders / correctness:** Undefined races cannot be legalized by stress testing. A watchdog cannot substitute for a schedulable stop path.

**Access gate:** No unbounded spin test; use valid memory types, scopes and ordering.

**Related:** R06 C22 C24 C25.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
