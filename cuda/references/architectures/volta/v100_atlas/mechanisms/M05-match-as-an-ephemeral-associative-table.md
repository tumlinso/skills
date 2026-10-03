# M05 — Match as an ephemeral associative table

> Equality groups can share reservations, decoding and reductions without a stored hash table.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** match, grouping, atomics, metadata.
**Prerequisites:** R06. **Evidence:** S03 S10.

## Established substrate [A; reachability C/P]

Match-style primitives return masks of equal-valued participating lanes. Their supported scalar/key semantics are exact; they are not approximate similarity search or global deduplication.

## Appropriation hypothesis

Elect a leader per equal destination, make one atomic reservation for the group and distribute compact positions by rank. Equal keys can share parameter loads or decoding. Aggregate repeated destinations before they consume cache/atomic bandwidth.

## Cost and rejection boundary

All-distinct keys create overhead with no aggregation benefit. Group size and skew determine leader workload. Multiword keys need correct comparison; numeric equality and bitwise equality differ for some floating values. Reservation is not payload publication. Global equivalence requires another level beyond one warp.

## Next reads

Compositions: C04 C35. Experiments: E05 E14.
