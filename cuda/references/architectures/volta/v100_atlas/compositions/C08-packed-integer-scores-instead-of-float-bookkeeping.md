# C08 — Packed integer scores instead of float bookkeeping

> Keep a bounded short score in the integer representation that produced it.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** DP4A, scoring, counting, quantization.
**Prerequisites:** M08 M09 R15. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Pack four signed or unsigned byte coefficients and state values into matching DP4A operands. A short dot then produces one integer score. Reuse a packed input across several score channels; delay conversion until a consumer genuinely needs floating arithmetic.

Before choosing the domain, prove |accumulator|+Σ|products| stays inside the supported accumulator range. Define clipping/quantization and signs explicitly. For binary support counting, also implement AND+POPC as the stronger specialized baseline.


## Why it could work

The hardware already sums packed products. Avoiding expand-to-float and re convert can matter more than the arithmetic instruction itself. Short categorical scores and bounded integer filters are natural semantics.

## Full cost and strongest baseline

Compare packed loads, conversion and resulting instruction mix over the complete chain. DP4A loses independent product outputs. A quantizer maintained elsewhere has a different amortization than a quantizer run for every score.

## Falsifier / rejection condition

Reject if packing is one-shot overhead, if range proofs force frequent slow fallback, or if a simpler bitset circuit computes the same result with less information movement.

**Experiment:** E13 E03 E39. This composition has not been benchmarked on a V100 here.
