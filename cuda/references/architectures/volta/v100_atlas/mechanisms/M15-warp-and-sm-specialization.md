# M15 — Warp and SM specialization

> Assign roles only when they can coexist and make progress.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** warp specialization, persistent, scheduling.
**Prerequisites:** R02 R06. **Evidence:** S01 S03 S30.

## Established substrate [A/D + H composition; reachability C/P]

Concurrent resident work is resource-limited and not a universal fairness promise. SM ID is an observation, not normal CUDA launch affinity. Cooperative launch changes admission requirements rather than erasing capacity constraints.

## Appropriation hypothesis

Give some work a loading, routing or queue-management role and other work a compute role. A persistent block can reuse local service state. Phase-specific roles may be better than permanently reserving idle warps.

## Cost and rejection boundary

A waiting consumer can starve its producer. All required block participants still reach barriers. Do not assume SM IDs are a compact semantic index. Skew can destroy a role split that worked on balanced traffic. Provide bounded stop/drain and capacity for producers.

## Next reads

Compositions: C19 C25 C34. Experiments: E16 E32.
