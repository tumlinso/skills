# C12 — Prefix and reductions by structured matrices

> An all-ones or triangular matrix can encode data movement and accumulation.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** reduction, scan, tensor.
**Prerequisites:** M26 M27 R05 R15. **Evidence:** S19 S03.

## Construction [H; reachability C/P]


For a short vector x, an all-ones row yields a sum. A lower-triangular all-ones matrix L gives inclusive prefix es y=Lx. Several independent scans can occupy different native subproblems; longer scans require inter-tile carry propagation.

Keep the output in a useful fragment layout when possible. Padding and repeated coefficient loading must be counted; structured coefficients should not be materialized expensively for every tiny operation.


## Why it could work

These are exact algebraic identities. Prior original research establishes the general tensor reduction/scan direction; this recipe focuses on matching native Volta fragments and complete downstream use.

## Full cost and strongest baseline

A warp scan has a short shuffle/add network and is a serious baseline. Tensor approaches perform padded arithmetic and may need layout conversion. Floating summation order changes the numerical result even when the real-number equation matches.

## Falsifier / rejection condition

Reject for a lone short scan when a few shuffles win, or when extraction/inter-tile carries erase the fused benefit. Compare many simultaneous scans and fragment-resident producers separately.

**Experiment:** E12 E10. This composition has not been benchmarked on a V100 here.
