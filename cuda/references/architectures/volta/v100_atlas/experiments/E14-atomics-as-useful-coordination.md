# E14 — Atomics as useful coordination

> How much semantic progress occurs per atomic transaction?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, atomics, as, useful, coordination.
**Prerequisites:** R12. **Evidence:** S03 S30.

**Question:** How much semantic progress occurs per atomic transaction?

**Minimal setup:** Benchmark reservation, merge and transition workloads with configurable target sharing and optional local aggregation.

**Sweep:** Contention, operation, width, returned-value dependence, distribution and failed CAS fraction.

**Discriminating observation:** Useful completed updates/second and latency tails, not merely raw issued attempts.

**Baseline:** Locally aggregated or phased alternatives at equal semantics.

**Confounders / correctness:** Atomicity does not publish other data. Hot lines and fairness can dominate.

**Access gate:** Supported operation and scope on the actual allocation; no race-based shortcut.

**Related:** C04 C24 C25 M29.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
