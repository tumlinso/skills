# C16 — Cancel intermediate transposes by composing ownership maps

> Keep data where the next instruction can already use it.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** fragments, layout, transpose, fusion.
**Prerequisites:** M25 M18 M04 R05. **Evidence:** S07 S22 S23.

## Construction [H; reachability C/P]


Write each producer and consumer layout as an explicit map from semantic coordinates to lane/register/shared positions. Compose the maps. If an intermediate canonicalization and subsequent retile are inverses, remove both and express the middle operation in the retained coordinates.

If only part of the maps cancel, route just the required subset. Replicated constants or a changed consumer tile may make the remaining exchange cheaper. Validate bijections and any intentional replication explicitly.


## Why it could work

A layout is an interface, not a cosmetic storage choice. Eliminating a store/barrier/load stage can save more than optimizing the arithmetic itself. Elementwise operations are often invariant under a shared permutation of their inputs and outputs.

## Full cost and strongest baseline

Count added address logic, shuffles and live registers. Direct accumulator compatibility is not guaranteed by matching matrix dimensions. Precision conversions can change the ownership and cost landscape.

## Falsifier / rejection condition

Reject when the fused representation creates spills, long dependencies or more expensive downstream access than the removed stages. Measure the full producer-to-consumer chain.

**Experiment:** E09 E04 E39. This composition has not been benchmarked on a V100 here.
