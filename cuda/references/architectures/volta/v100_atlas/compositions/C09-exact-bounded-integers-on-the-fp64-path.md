# C09 — Exact bounded integers on the FP64 path

> Move a proved arithmetic subproblem rather than blindly seeking idle units.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** FP64, integer, pipeline, exactness.
**Prerequisites:** M11 M16 R15. **Evidence:** S01 S03.

## Construction [H; reachability C/P]


Identify an integer subproblem whose inputs, products and every partial sum remain exactly representable in binary64. Convert once, perform several operations in that domain, then convert back under a proved rounding/range contract. Candidate roles include bounded accumulations or index-polynomial evaluation.

The condition is stronger than “each input is below 2^53.” Intermediate multiplication and cancellation paths must also be safe. Division, remainder and bitwise operations generally need separate derivations.


## Why it could work

The same exact finite arithmetic can sometimes use a different execution resource. This is a capacity-allocation hypothesis, not an assertion that FP64 is always cheaper than integer work.

## Full cost and strongest baseline

Include conversions,64-bit register pressure, dependency length and shared issue. Compare native integer sequences with equal work. Benefit requires an actual bottleneck and an amortized domain change.

## Falsifier / rejection condition

Reject when any intermediate loses integer exactness, when conversions dominate, or when the supposed alternate pipe contends with the same limiting resource.

**Experiment:** E01 E03 E13. This composition has not been benchmarked on a V100 here.
