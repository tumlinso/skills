# C15 — High/low precision expansion as a composite operator

> Build additional accuracy from multiple native products with an explicit residual.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** precision, tensor, expansion.
**Prerequisites:** M28 M09 R15. **Evidence:** S21 S20.

## Construction [H; reachability C/P]


Split A=Ah+Al and B=Bh+Bl into representable components. Compute AhBh+AhBl+AlBh and optionally AlBl. Omitting the last term leaves exact-algebra residual AlBl, with norm bound ||Al||||Bl|| for a compatible norm.

Actual output error also contains all input splitting, product accumulation and combination errors. Choose scales so the low component is meaningful and representable; a poorly scaled split may simply underflow.


## Why it could work

The expansion exposes more useful work to native half-input products while separating the accuracy budget into terms. It can be tuned by dropping or retaining a correction rather than assuming a nonexistent full-FP32 tensor instruction.

## Full cost and strongest baseline

Compare native FP32, compensated approaches and problem-specific reformulations. Three/four products, conversions and extra live fragments can exhaust registers or bandwidth. Conditioning determines whether the residual is acceptable.

## Falsifier / rejection condition

Reject when the actual numerical tests violate the promised bound, or when correction work and routing exceed the chosen conventional precision path.

**Experiment:** E10 E12 E39. This composition has not been benchmarked on a V100 here.
