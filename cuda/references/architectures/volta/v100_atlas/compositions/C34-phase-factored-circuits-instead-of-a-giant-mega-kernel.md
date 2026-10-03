# C34 — Phase-factored circuits instead of a giant mega kernel

> Keep the hot instruction and register working set small enough to be useful.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** instruction cache, persistent, phases.
**Prerequisites:** M17 M30 M33 R02. **Evidence:** S04 S05 S30.

## Construction [H; reachability C/P]


Split a broad rule palette into a small hot circuit and infrequent exceptional paths. Factor repeated instruction sequences or use a compact resident interpreter only for the shared core. Group tasks by operator/shape to reduce divergent dispatch.

Compare a fully unrolled version, a factored version, graphs and separate kernels. Keep semantic work and data reuse comparable.


## Why it could work

Instruction fetch and live register state are real working sets. Removing repeated code or rare branches can improve the useful machine even when it adds a small dispatch operation.

## Full cost and strongest baseline

Phase boundaries can force data stores, barriers or lost compiler optimization. A smaller binary is not automatically faster. Count operand reloads and hand off cost along with instruction cache behavior.

## Falsifier / rejection condition

Reject if factoring merely moves cost into dispatch/state material i zat i on or if the original instruction footprint was not a bottleneck.

**Experiment:** E02 E30 E32 E39. This composition has not been benchmarked on a V100 here.
