# C07 — Guard-digit convolution using ordinary integer multiplication

> Use positional encoding to turn a bounded small convolution into multiply and extract.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** packing, integer, polynomial, convolution.
**Prerequisites:** M09 M11 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Choose base B=2^g. Encode A=Σa_iB^i and D=Σd_jB^j. Their integer product has coefficient c_k=Σ_(i+j=k)a_i d_j at digit k **only if every coefficient is below B**, so no digit carry occurs, and the entire product fits the selected integer width.

For four digits in 0..3, maximum coefficient≤36. g=6 gives sufficient guard space; seven output digits occupy42 bits. Extract each coefficient with shifts and masks. Signed coefficients need a separately proved bias/correction scheme.


## Why it could work

This is exact schoolbook polynomial convolution embedded in integer positional arithmetic. Multiplication becomes a constrained small algebra engine. It is not carry less multiplication, arbitrary semiring arithmetic or an unlimited packing trick.

## Full cost and strongest baseline

Count encoding,64-bit multiply implementation and extraction. Compare DP4A, scalar multiply-add and a tensor construction where shapes align. Reuse of packed operands is crucial. Width and coefficient bounds must be checked for every chosen problem size.

## Falsifier / rejection condition

Reject on any possible cross-digit carry, overflow or unsupported signed correction. The CPU suite deliberately includes an insufficient-guard negative control to prevent over generalizing the identity.

**Experiment:** E01 E13. This composition has not been benchmarked on a V100 here.
