# E16 — Persistent roles and residency

> When does retained state repay queueing and reserved resources?

**Status:** GPU_RUN (implemented subset only; see measured coverage). **Original protocol status:** NOT_RUN_ON_GPU ([immutable original card](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E16.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

Six correctness-valid GPU cases compare cooperative residency, finite batching, and graph replay for exact sums over 32 tasks × 8 rounds and 256 tasks × 32 rounds. Resident medians are 14.336 and 35.840 microseconds. Batched and graph-replay medians are 7.168 microseconds at both selected sizes. The recorded sums are 528 and 32,896. These are reported kernel/graph execution timings; one-time graph capture/setup is outside the repeated execution interval.

[Measured summary](evidence/v100-20261006/E16.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md) · [sync.cu: resident_work and batched_work](../benchmarks/native/sync.cu#L126)

## Meaning through representation and execution

- **Supports:** The three execution variants preserve the selected sum, while the resident variant is slower for these task counts and rounds.
- **Design implication (inference):** Resident roles are a scheduling/resource choice whose value depends on enough work or state reuse to repay residency costs.
- **Does not establish:** Starvation freedom, a residency advantage under skew or expensive state reuse, or a new computation/algebra.
- **Original protocol gaps:** The task-size, skew, role-split, footprint, occupancy, and stop/drain sweeps are not covered by these six cases.
