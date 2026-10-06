# C17 — Operand-read hypergraph coloring

> Optimize how values reach instructions, not only where values are stored.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** register banks, reuse, SASS.
**Prerequisites:** M12 M13 R02 R10. **Evidence:** S04 S05 S11.

## Construction [H; reachability B; source-level C alternatives]


For a hot instruction sequence, record each distinct register read and any reuse-assisted read. Treat instructions as hyperedges over values. Search assignments or amortized copies that reduce repeated bank conflicts while preserving every def/use and dependency.

Use source restructuring first. Escalate to a pinned binary experiment only when it isolates a real compiler limitation. Keep a deterministic transformation and original binary for differential testing.


## Why it could work

Bank supply can limit an unchanged arithmetic sequence. Reuse removes pressure from the graph, so a globally sensible assignment may differ from a naïve “alternate all register numbers” rule.

## Full cost and strongest baseline

Include inserted moves, live-range extension, occupancy and conflicts introduced elsewhere. The empirical bank model is not a universal PTX contract. Compare equal instruction work and clocks before attributing a result.

## Falsifier / rejection condition

Reject any transformation without complete executable metadata/dependency validation. Reject the optimization if its local port gain disappears in the complete kernel.

**Experiment:** E04 E30. This composition has not been benchmarked on a V100 here.
