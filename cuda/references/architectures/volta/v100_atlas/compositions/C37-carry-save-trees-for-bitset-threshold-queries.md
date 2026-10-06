# C37 — Carry-save trees for bitset threshold queries

> Count many masks without expanding each bit to a scalar counter.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** bitsets, threshold, reduction, Boolean.
**Prerequisites:** M01 M02 M06 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Combine three equal-weight planes a, b, c into sum=a^b^c at the same weight and carry=majority(a, b, c) at twice the weight. Repeat as a carry-save tree until one plane remains per weight. For each bit position the weighted planes encode how many in put masks contain it.

Evaluate a threshold directly on those planes, or compute total population as Σ_j 2^j·popcount(plane_j). The two outputs answer different questions: per-position multiplicity versus aggregate count.


## Why it could work

Carry remains an explicit plane, so unrelated bit positions never interfere. Many scalar counters are replaced by a network of word gates. Threshold ing can avoid full binary decode.

## Full cost and strongest baseline

Compare serial popcounts for an aggregate count and packed/scalar counts for per-position results. Plane count, register pressure and threshold circuit cost matter. A simple aggregate may not justify the tree.

## Falsifier / rejection condition

Reject when only one total count is needed and direct POPC reduction wins, or when the number of in put planes exhausts useful register capacity.

**Experiment:** E01 E13 E39. This composition has not been benchmarked on a V100 here.
