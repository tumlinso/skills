# E12 — Tensor circuits versus structured SIMT

> Does a small transform benefit from MMA once routing is included?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
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


## Measured coverage (2026-10-06)

The operator was a block-diagonal 16×16 matrix `M = diag(H4/2, H4/2, H4/2, H4/2)` applied to one fixed 16-vector `x`, with `H4` the 4×4 Hadamard matrix. Each kernel reloads the same `x`, recomputes `M x` per iteration and accumulates `Y_r = r(M x)`; it does not feed output back as `M^r x`. Four GPU cases passed at transform counts 16/256 and one/eight iterations, comparing shuffle/add with FP16 WMMA. Kernel median/p95 at transform count 16 were 0.005120/0.006144 ms for both; at transform count 256 they were 0.007168/0.007168 ms and 0.006144/0.007168 ms respectively. Maximum absolute error was 1.19e-7/2.38e-7 for shuffle/add and 4.23e-4 for WMMA. These resident-kernel timings omit full preparation/extraction costs. Implementation: [`run_e12`](../benchmarks/native/tensor.cu#L510). [Measured summary](evidence/v100-20261006/E12.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: The tested padded 4×4-block transform implementations and their observed error/timing for two sizes.
- Design implication (inference): The tested operator factors into four independent 4-variable Hadamard blocks, each naturally represented by a four-lane butterfly/shuffle; padding the matrix to 16×16 adds no semantic coupling. MMA is a better structural fit when the real operator is dense or shares work across the tile and its precision is acceptable. Any benefit from retaining fragments across multiple operators remains unmeasured.
- Does not establish: A recurrent state update `M^r x`, a general coupled 16-variable model, a native-fragment multi-operator pipeline benefit, or an end-to-end tensor-path advantage.
- Original protocol gaps: Broader transform/reuse/precision sweeps and complete routing, padding, conversion and extraction costs were not compared.
