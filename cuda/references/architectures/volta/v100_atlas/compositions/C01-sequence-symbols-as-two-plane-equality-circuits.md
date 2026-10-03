# C01 — Sequence symbols as two-plane equality circuits

> Change symbol comparison into a few word-wide gates.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** sequence, support, bitsets.
**Prerequisites:** M01 M02 M06. **Evidence:** S03 S08.

## Construction [H; reachability C/P]


Encode a four-symbol alphabet by two planes x0, x1. For another sequence y0, y1:

```
eq = ~((x0 ^ y0) | (x1 ^ y1)) & valid
matches = popcount(eq)
```

Position-shifted comparisons use shifts plus explicit cross-word carry or neighbor-lane exchange. A fifth ambiguous symbol needs another plane or a separate validity/wildcard rule; do not silently collapse it into one of the four. Compound motifs can reuse aligned planes and Boolean masks.


## Why it could work

Equality decomposes exactly into equality of encoded bits. The intermediate mask is directly useful for routing or support queries, so a scalar match array need never exist. Shifts turn positional relations into wiring.

## Full cost and strongest baseline

Compare byte-packed XOR/permutation and ordinary vector loads. Building bitplanes for one short comparison can lose. Include boundary symbols, reverse orientation and ambiguous-symbol semantics. Match counting and edit distance are different algorithms; this does not solve arbitrary alignment by renaming it.

## Falsifier / rejection condition

Reject when frequent orientation/window changes require more transposition than comparison, or when the consuming operator immediately needs expanded scalar symbols.

**Experiment:** E01 E13. This composition has not been benchmarked on a V100 here.
