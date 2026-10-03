# C14 — Certified approximate screening with exact refinement

> Use fast approximate algebra to avoid expensive exact work without changing the final decision.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** filter, precision, sparse support, refinement.
**Prerequisites:** M28 M02 R15. **Evidence:** S20 S21.

## Construction [H; reachability C/P]


Suppose a score s is compared with τ and a fast approximation ŝ has a proved error bound ε. Accept when ŝ−ε≥τ; reject when ŝ+ε<τ; otherwise refine exactly. Store ambiguous cases as a mask and compact them using rank/select.

The bound must include input quantization, actual tensor/SFU accumulation behavior and extraction. A heuristic margin may still be a useful approximate algorithm, but it must not be labeled certified.


## Why it could work

The decision follows interval containment. Most objects far from the threshold can avoid expensive work while final answers remain exact. This is a way to compose different units according to uncertainty rather than one fixed arithmetic policy.

## Full cost and strongest baseline

Compare direct exact evaluation and an inexpensive integer/bitset prefilter. Include bound construction, ambiguity traffic and refinement scheduling. Input distributions nearτ can make almost every item ambiguous.

## Falsifier / rejection condition

Reject the exactness claim without a valid bound. Reject the performance idea if fallback and bookkeeping cost exceed work avoided, even when the fast stage has impressive throughput.

**Experiment:** E10 E11 E39. This composition has not been benchmarked on a V100 here.
