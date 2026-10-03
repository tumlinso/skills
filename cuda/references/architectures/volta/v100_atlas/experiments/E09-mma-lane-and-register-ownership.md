# E09 — MMA lane and register ownership

> Does the explicit sm70 fragment mapping match the compiled instruction?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, mma, lane, and, register, ownership.
**Prerequisites:** R12. **Evidence:** S03 S22 S23.

**Question:** Does the explicit sm70 fragment mapping match the compiled instruction?

**Minimal setup:** Use one-hot/basis inputs and uniquely labeled accumulators. Store raw per-lane outputs before any canonicalizing wrapper.

**Sweep:** Each lane, fragment element, group, row/column form and accumulator type separately.

**Discriminating observation:** Full coordinate coverage and exact expected ownership for the tested explicit PTX form.

**Baseline:** CPU coordinate map and scalar small matrix multiplication.

**Confounders / correctness:** Opaque WMMA layouts are not the explicit PTX contract; all required lanes execute the instruction.

**Access gate:** Compile supported sm70 forms and inspect SASS before interpreting output.

**Related:** R05 M24 M25 C10 C16.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
