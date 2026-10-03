# C36 — Compose lane, bank and fragment permutations

> Optimize the entire path rather than one attractive memory layout.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** layout, transpose, shared, fragments.
**Prerequisites:** M18 M25 M22 R05. **Evidence:** S22 S23 S30.

## Construction [H; reachability C/P]


Represent each layout as a mapping between semantic coordinates and physical positions. Choose a producer layout that coalesces global loads, then a shared swizzle and fragment assignment whose compositions minimize the exchanges required by later operators.

Test the composite map for coverage, bijection or intentional replication. An inverse pair of transposes may disappear. A mapping that optimizes one stage but destroys the next is not globally good.


## Why it could work

Permutation composition is exact algebra on indexes. It can eliminate movement rather than merely making each movement faster. Ownership maps are reusable interfaces between kernels or fused stages.

## Full cost and strongest baseline

Count address instructions, padding, bank conflicts, register pressure and final output order. Some maps are cheap only at fixed shape; dynamic shapes need fallbacks. Actual physical HBM hashes are not assumed known.

## Falsifier / rejection condition

Reject when extra index arithmetic or live state exceeds the removed traffic, or when the mapping relies on undefined WMMA fragment internals.

**Experiment:** E01 E06 E09 E39. This composition has not been benchmarked on a V100 here.
