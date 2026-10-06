# E10 — Tensor numerical fingerprint

> Which target-specific rounding and range properties matter to an encoding?

**Status:** GPU_RUN. **Original protocol status:** NOT_RUN_ON_GPU. **Original archive:** [commit `5c1f805db80a81f7476ede8292abba69821d104f`](https://github.com/tumlinso/gpu_circuit_bending_atlas/commit/5c1f805db80a81f7476ede8292abba69821d104f). **Depth:** 4.
**Read when:** experiment, tensor, numerical, fingerprint.
**Prerequisites:** R12. **Evidence:** S20 S21 S03.

**Question:** Which target-specific rounding and range properties matter to an encoding?

**Minimal setup:** Use targeted exponent gaps, cancellation, ties, subnormals, zeros, large bounded counts and high/low expansions; retain exact references where possible.

**Sweep:** Operand placement, sign, accumulator magnitude, contraction length and conversion order.

**Discriminating observation:** A numerical feature table, not only mean error on random matrices.

**Baseline:** Exact integer/rational reference plus explicitly specified scalar floating evaluation orders.

**Confounders / correctness:** Input conversion can dominate; equality on easy nonnegative cases does not prove arbitrary FMA equivalence.

**Access gate:** No claim of exact tensor counting or certified filtering before this gate and a bound.

**Related:** R15 C11 C14 C15 M28.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.


## Measured coverage (2026-10-06)

The measured unit was an eight-case WMMA numerical fingerprint: cancellation, exponent gap, halfway tie, subnormal input, signed zero, bounded integer count, high/low residual and large-first placement. Two GPU cases passed at sizes 16/256 (one/eight iterations) against long-double exact-input and explicit scalar-FMA references. All recorded cases passed the stated case-level diagnostic gamma16 bound. Maximum absolute error versus long-double was 1.0000001 at size 16 and 8.0000005 at size 256. Kernel-only median/p95 were 0.005120/0.006144 ms. The bound is not a claim about proprietary tensor ordering or subnormal handling. Implementation: [`run_e10`](../benchmarks/native/tensor.cu#L278). [Measured summary](evidence/v100-20261006/E10.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- Supports: A targeted fingerprint for the tested input corpus, operand placements and WMMA form.
- Design implication (inference): Treat these cases as prompts for conservative, representation-specific error bounds.
- Does not establish: General numerical proof, arbitrary FMA equivalence, exact tensor counting or a certified filter.
- Original protocol gaps: Broader signs/ranges/contraction lengths, adversarial placement search, a theorem-backed bound and downstream decision-error validation are absent.
