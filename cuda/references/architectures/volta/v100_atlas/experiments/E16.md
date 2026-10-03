# E16 — Persistent roles and residency

> When does retained state repay queueing and reserved resources?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, persistent, roles, and, residency.
**Prerequisites:** R12. **Evidence:** S01 S30.

**Question:** When does retained state repay queueing and reserved resources?

**Minimal setup:** Compare bounded resident executors, batched kernels and graphs with the same task stream. Make producer progress explicit.

**Sweep:** Task size, skew, role split, register/shared footprint, occupancy and stop/drain behavior.

**Discriminating observation:** End-to-end throughput/tails and state-reuse benefit without starvation.

**Baseline:** Properly batched and graph-replayed conventional execution.

**Confounders / correctness:** Assuming all blocks are concurrently resident or treating smid as launch affinity invalidates the design.

**Access gate:** Supported cooperative admission where used; otherwise no global spin barrier.

**Related:** C19 C25 C34 M15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
