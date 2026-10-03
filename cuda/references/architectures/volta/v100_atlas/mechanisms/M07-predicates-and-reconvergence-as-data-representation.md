# M07 — Predicates and reconvergence as data representation

> Replace control only when masked work or routing is cheaper.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** predication, branch elimination, control.
**Prerequisites:** R02 R04 R06. **Evidence:** S03 S05 S10.

## Established substrate [A/D; reachability C/P/B]

Predicated lane behavior, warp instruction issue and branch/reconvergence cost are different. Volta independent-thread scheduling does not eliminate convergence or memory-order requirements. Predicate storage is finite and specialized.

## Appropriation hypothesis

Express short transitions as predicate-selected updates, or first group state into homogeneous cohorts before a longer operation. Fuse conditions into one mask. A small resident interpreter can use a fixed control circuit rather than a divergent switch for every object.

## Cost and rejection boundary

Executing expensive invalid alternatives merely to discard them is not a win. Predicated instructions can still consume issue opportunities. Do not rely on undocumented fault suppression. Long branch bodies may favor real branches. Measure active useful work, instruction count and divergence separately.

## Next reads

Compositions: C00 C06 C34. Experiments: E05 E30.
