# E24 — Fault and access-counter policy

> Is coarse remote-access feedback useful before the phase ends?

**Status:** GPU_RUN (implemented subset only; see measured coverage). **Original protocol status:** NOT_RUN_ON_GPU ([immutable original card](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E24.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

Eight correctness-valid GPU cases run the same uint32-to-uint64 sum over 4,096 and 65,536 elements using CPU-first managed access, prefetch, advised prefetch, and explicit device allocation plus H2D copy. Each case has 30 samples and identical checksums across placements at each size. Host end-to-end medians at 4,096 elements range from 0.455 ms (explicit copy) to 0.558 ms (CPU-first managed); at 65,536 they range from 26.419 to 26.895 ms. The timed managed path includes demand migration or prefetch and reduction work; explicit placement includes its H2D copy and reduction. CPU-residency restoration before managed samples is excluded. No migration-cause counters were collected.

[Measured summary](evidence/v100-20261006/E24.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md) · [memory.cu: reduce_u32 and managed-memory variants](../benchmarks/native/memory.cu#L109)

## Meaning through representation and execution

- **Supports:** Total host-visible cost for these explicit/managed placement paths when each performs the same reduction at the two tested sizes.
- **Design implication (inference):** Compare placement policies using a complete path that charges each policy's own timed movement step and the common computation.
- **Does not establish:** A causal migration mechanism, complete fault/access-counter visibility, or a general managed-memory policy advantage.
- **Original protocol gaps:** No migration attribution, controlled locality sweep, phase-duration/reuse sweep, or page-table evidence is part of these results.
