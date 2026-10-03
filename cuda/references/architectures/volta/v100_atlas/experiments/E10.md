# E10 — Tensor numerical fingerprint

> Which target-specific rounding and range properties matter to an encoding?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
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
