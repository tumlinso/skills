# C11 — Tensor cores as common-neighbor counters

> Encode a batch of set intersections as binary matrix products, then test against bitsets.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** support, intersection, Jaccard, tensor.
**Prerequisites:** M26 M08 M02 R15. **Evidence:** S03 S19 S20.

## Construction [H; reachability C/P]


Let row X_i and row Y_j be binary incidence vectors over the same universe. C=XYᵀ gives intersection counts; union=|X_i|+|Y_j|−C_ij. Keep cardinalities separately and define the empty-union case for any similarity ratio.

Tile the contraction with supported half-input MMA and a validated bounded accumulation regime. For long universes, chunk and combine counts using exact integer arithmetic. Alternative output semantics include thresholded overlap rather than the full matrix.


## Why it could work

The algebra is exact over integers because binary multiplication is conjunction and addition counts. Tensor hardware can process many overlapping questions sharing the same decoded blocks. Whether its numerical path preserves the intended counts is a separate validation gate.

## Full cost and strongest baseline

AND+POPC on packed words is the primary baseline; DP4A is another. Tensor expansion moves many more bytes than packed support. High reuse and many pairwise queries may repay decoding; isolated intersections probably have a different optimum.

## Falsifier / rejection condition

Reject when expansion/padding/output traffic dominates, when count exactness fails, or when the application never needs the dense set of pairwise answers being computed.

**Experiment:** E10 E11 E13. This composition has not been benchmarked on a V100 here.
