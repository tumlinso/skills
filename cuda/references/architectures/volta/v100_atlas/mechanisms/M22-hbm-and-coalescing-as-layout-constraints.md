# M22 — HBM and coalescing as layout constraints

> Bring useful fields together before optimizing the load instruction.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** HBM, coalescing, partitioning.
**Prerequisites:** R03 R11. **Evidence:** S02 S04 S30.

## Established substrate [D/E; reachability C/P]

Warp aggregation, sectors and memory-controller structure impose transaction granularity. One logical scalar request can move substantially more data. Not every address-to-bank mapping is publicly established.

## Appropriation hypothesis

Pack co-used state into the same transactions; separate cold metadata; order work to spread measured partition contention. Treat a discovered mapping as a tunable performance hint rather than immutable correctness state.

## Cost and rejection boundary

Optimize useful-byte fraction and reuse, not only G B/s. Allocation/page changes can alter inferred mappings. Copies, peer service and local work contend for owner HBM. A bidirectional link headline is not comparable to a one-way local-read rate.

## Next reads

Compositions: C23 C38. Experiments: E07 E08 E17 E20.
