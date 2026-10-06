# M16 — Instruction-level parallelism and useful overlap

> Hide a dependency with required work, not with more busy work.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** ILP, latency hiding, occupancy.
**Prerequisites:** R02 R11 R14. **Evidence:** S01 S04.

## Established substrate [D/E; reachability C/P/B]

Different execution resources can overlap, but issue, operands and dependence chains still constrain them. Occupancy is not equivalent to eligible independent work. Outstanding requests are finite.

## Appropriation hypothesis

Interleave several local microcircuits, prepare future addresses and support masks, or prefetch the next tile while current arithmetic runs. A representation that exposes independence can outperform one with fewer but serial operations.

## Cost and rejection boundary

Compare equal semantic work in isolated, serial and interleaved schedules. Track register count and memory traffic. Do not sum advertised peaks. An apparently better utilization number can simply reflect extra work absent from the baseline.

## Next reads

Compositions: C18 C19. Experiments: E02 E03.
