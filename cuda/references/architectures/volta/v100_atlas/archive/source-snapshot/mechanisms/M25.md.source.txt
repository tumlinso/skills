# M25 — Fragment-native intermediates

> A result is already a usable distributed representation; canonical memory is optional.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** fragments, layout, registers, fusion.
**Prerequisites:** R05 R15. **Evidence:** S03 S07 S22 S23.

## Established substrate [A/E; reachability P/C/B]

Explicit PTX forms have defined lane/register ownership, while high-level WMMA fragment layout is not a portable raw-storage contract. Accumulator type can change conversion and shuffle costs.

## Appropriation hypothesis

Fuse masking, normalization, small transforms or another MMA in the existing producer ownership. Compose layout mappings so intermediate transposes cancel. An extra boundary permutation can remove repeated shared store/barrier/load phases.

## Cost and rejection boundary

Matching matrix dimensions does not imply direct fragment compatibility. Smaller move counts can lengthen dependencies or live ranges. FP16 storage may save registers yet lose on conversion or accuracy. Use ownership maps and complete pipeline timing.

## Next reads

Compositions: C16 C10. Experiments: E09 E10 E39.
