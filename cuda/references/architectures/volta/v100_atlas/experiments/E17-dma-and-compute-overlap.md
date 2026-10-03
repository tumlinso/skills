# E17 — DMA and compute overlap

> Which actors and routes make progress concurrently on this machine?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, dma, and, compute, overlap.
**Prerequisites:** R12. **Evidence:** S15 S30 S32.

**Question:** Which actors and routes make progress concurrently on this machine?

**Minimal setup:** Time each copy path and compute workload alone, serially and concurrently with explicit legal buffer lifetimes.

**Sweep:** Size, direction, buffer depth, local/peer/host routes and compute memory intensity.

**Discriminating observation:** A contention/overlap matrix including owner HBM and critical-path effects.

**Baseline:** SM copy/transform and public asynchronous copy paths.

**Confounders / correctness:** Asynchronous return is not physical overlap; roots, copy-engine assignment and power may be shared.

**Access gate:** No reset or clock changes; pinned allocation and actual engine capabilities recorded.

**Related:** C19 C23 C26 M36 R14.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
