# M28 — Mixed precision and certified decisions

> Approximate arithmetic is most useful when the final decision has an exact contract.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** precision, filter, refinement.
**Prerequisites:** R15. **Evidence:** S20 S21 S03.

## Established substrate [E + H composition; reachability C/P]

Input quantization, internal accumulation and output conversion are separate error sources. Targeted empirical evidence argues against assuming arbitrary scalar IEEE FMA equivalence for Volta tensors. Expansion requires additional operations.

## Appropriation hypothesis

Split values into high/low parts or compute a cheap score with an explicit error bound. Refine only ambiguous threshold cases using integer, bitset or higher precision work. Preserve a compact ambiguity mask for routing.

## Cost and rejection boundary

A guessed margin can silently remove true candidates. Cancellation/exponent gaps matter more than average error. Measure refinement fraction and conversion costs. Nearly universal refinement makes the filter strictly worse. No native full FP32 tensor mode is implied.

## Next reads

Compositions: C14 C15. Experiments: E10 E11 E39.
