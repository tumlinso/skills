# M09 — Packed SIMD and conversions as state operators

> Saturation, rounding and comparisons can embody transitions rather than bookkeeping.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** packing, conversion, quantization, state.
**Prerequisites:** R04 R15. **Evidence:** S08 S09 S03.

## Established substrate [A semantics; reachability C/P]

Packed arithmetic/comparison and conversion intrinsics expose defined semantics, not guaranteed single-opcode lowering. Numeric conversion differs from bit reinterpretation; ordinary packed addition can leak carries between intended fields.

## Appropriation hypothesis

Use bounded saturating states, packed comparisons or quantization directly into the format required by a late rD P4A/bitplane stage. Rounding can implement a discretization boundary; a conversion can remove a whole intermediate representation.

## Cost and rejection boundary

Inspect expansion and execution pipe. Validate signs, ties, out-of-range cases and guard bits. Per-field independence needs a proof or a saturating/SIMD form. Domain switching every instruction can cost more than remaining in one numerical format. Keep exact fallback for sensitive thresholds.

## Next reads

Compositions: C07 C08 C15. Experiments: E13 E03.
