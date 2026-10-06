# E09 — MMA lane and register ownership

> Does the explicit sm70 fragment mapping match the compiled instruction?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
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


## Measured coverage (2026-10-06)

Two GPU cases passed: explicit `mma.sync.aligned.m8n8k4.row.col.f32.f16.f16.f32` with one-hot/basis inputs and a WMMA one-hot fragment. The explicit PTX case saved raw per-lane accumulators before canonicalization and covered 256 documented coordinates with zero CPU-map error. WMMA produced canonical output with zero error against its FP16-input oracle and wrote 256 finite raw fragment slots; that check did not verify which lane owns each slot. Each was one small kernel, median about 0.005120 ms over 30 timing samples. Implementation: [`run_e09_ptx`](../benchmarks/native/tensor.cu#L193), [`run_e09_wmma`](../benchmarks/native/tensor.cu#L243). [Measured summary](evidence/v100-20261006/E09.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: The documented lane/register coordinate mapping for the explicit PTX `m8n8k4` form. The WMMA case supports canonical output correctness and finite writes only; it did not verify WMMA fragment ownership.
- Design implication (inference): Reuse the PTX coordinate map only for that documented instruction form. Treat WMMA lane ownership as opaque unless a separate mapping check establishes it.
- Does not establish: WMMA lane-to-fragment ownership, an arbitrary scientific MMA mapping, portability of opaque WMMA layouts, or end-to-end performance.
- Original protocol gaps: Other forms/types, exhaustive fragment-element/group/row-column sweeps, and application-level tests remain absent.
