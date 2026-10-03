# E12 — Tensor circuits versus structured SIMT

> Does a small transform benefit from MMA once routing is included?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, tensor, circuits, versus, structured, simt.
**Prerequisites:** R12. **Evidence:** S19 S24 S22.

**Question:** Does a small transform benefit from MMA once routing is included?

**Minimal setup:** Compare prefix, reduction, Hadamard/stencil or butterfly components with direct shuffle/add circuits and tensor implementations.

**Sweep:** Number of simultaneous transforms, coefficient reuse, fragment-resident input/output and precision.

**Discriminating observation:** The regime where native fragments and reuse beat fewer structured SIMT operations.

**Baseline:** Hand-structured shuffle/add implementation and suitable library path.

**Confounders / correctness:** Floating summation order, zero padding, normalization and extraction must be equivalent or bounded.

**Access gate:** Use verified fragment mapping and supported sm70 formats.

**Related:** C10 C12 C13 C15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
