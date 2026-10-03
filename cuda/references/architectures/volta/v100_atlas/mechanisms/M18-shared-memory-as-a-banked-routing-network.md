# M18 — Shared memory as a banked routing network

> Layout can make broadcast and exchange the main computation.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** shared, banks, transpose, routing.
**Prerequisites:** R03 R06. **Evidence:** S01 S30 S04.

## Established substrate [A/D/E; reachability C/P]

Shared storage is block-scoped and banked with documented broadcast cases. Its capacity is coupled to the shared/L1 configuration. Conflicts serialize accesses without promising a useful arbitration order.

## Appropriation hypothesis

Assign local ownership to lanes/banks, swizzle repeated transposes and deliberately broadcast common coefficients. Store a scratch graph or transition table in a form chosen for its consumer. A shared layout can feed tensor fragments without a canonical intermediate.

## Cost and rejection boundary

Padding/swizzling costs addresses and can hurt the following stage. Distinct words in one bank are not a broadcast. Conflicts cannot substitute for atomics or barriers. Compare tiny exchanges to shuffles and count both producer and consumer phases.

## Next reads

Compositions: C16 C36. Experiments: E06 E09.
