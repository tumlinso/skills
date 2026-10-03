# M24 — Four native tensor microcircuits per warp

> The documented sm70 decomposition permits smaller semantic problems than conventional WMMA usage suggests.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** HMMA, tensor, small algebra.
**Prerequisites:** R05 R15. **Evidence:** S03 S22 S23.

## Established substrate [A/D; reachability P/C]

The supported half-input m8n8k4 form contains four independent 8×8×4 products but remains a collective warp instruction. Explicit lane ownership differs from arbitrary WMMA internals.

## Appropriation hypothesis

Map four graph patches, state-transition banks, basis changes or local reductions into one warp. Batch by reusable structure instead of only by examples. Keep fragments in a native representation for subsequent local work.

## Cost and rejection boundary

Pay for operand construction, zero padding, conversion and extraction. A vector reshaped into a tile does not preserve any desired operator for free. Do not execute only one 8-thread group or import later tensor formats. Validate mapping and numeric bounds first.

## Next reads

Compositions: C10 C11 C12 C13. Experiments: E09 E10 E12.
