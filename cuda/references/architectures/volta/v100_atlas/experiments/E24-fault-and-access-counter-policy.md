# E24 — Fault and access-counter policy

> Is coarse remote-access feedback useful before the phase ends?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, fault, and, access-counter, policy.
**Prerequisites:** R12. **Evidence:** S16 S28 S29 S31.

**Question:** Is coarse remote-access feedback useful before the phase ends?

**Minimal setup:** Observe supported managed-memory advice/prefetch/migration behavior and available notifications under controlled locality phases.

**Sweep:** Phase duration, reuse, working set, advice and owner placement.

**Discriminating observation:** Policy lag, migration traffic and total time, not just fault counts.

**Baseline:** Explicit placement and fixed managed policies.

**Confounders / correctness:** Notifications may be driver-owned; shared-source defaults are not fixed hardware configuration. Avoid intentional overflow.

**Access gate:** No direct ATS/PTE changes without a separately established platform/driver contract.

**Related:** C30 C32 M41 M42.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
