# E17 — DMA and compute overlap

> Which actors and routes make progress concurrently on this machine?

**Status:** GPU_RUN (implemented subset only; see measured coverage). **Original protocol status:** NOT_RUN_ON_GPU ([immutable original card](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E17.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

Six correctness-valid GPU cases cover pageable and pinned serial H2D–increment–D2H paths and a pinned two-slot pipeline at 16 KiB and 4 MiB per slot. The semantic check is output[i] = input[i] + 1. Each case reports 30 complete-path samples. At 4 MiB, the one-buffer pinned serial median is 1.334 ms. The two-slot pipeline processes two 4 MiB inputs (8 MiB total) and has a 2.071 ms median. That path includes both copies, the increment kernel, per-slot event dependencies, and final stream synchronization. The report's Nsight Systems timeline is separate from these unprofiled timings.

[Measured summary](evidence/v100-20261006/E17.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md) · [transport.cu: increment_kernel and run_e17](../benchmarks/native/transport.cu#L86)

## Meaning through representation and execution

- **Supports:** Correct per-slot results with explicit ready/computed event edges and separate pinned host/device buffers.
- **Design implication (inference):** Event edges encode safe source/destination reuse while allowing commands to be submitted across copy and compute streams.
- **Does not establish:** An equal-work speedup: the two-slot case processes 8 MiB versus 4 MiB for the quoted serial case. It also does not prove simultaneous physical DMA/compute execution from dependency structure alone.
- **Original protocol gaps:** The matrix does not isolate individual engine routes, directions, owner-HBM contention, or a same-payload serial-versus-concurrent overlap comparison.
