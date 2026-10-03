# M19 — Barriers as phase boundaries

> A phase machine needs known participants and a schedulable producer.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** barriers, synchronization, phases.
**Prerequisites:** R06. **Evidence:** S03 S30.

## Established substrate [A; reachability C/P]

Warp, CTA and cooperative-grid barriers have different participant and ordering contracts. Named resources are finite. Ordinary oversubscribed grids cannot safely assume a global spin barrier.

## Appropriation hypothesis

Publish a tile, exchange state ownership or recycle a buffer at explicit phase boundaries. Independent work between phases can hide production delay. Count synchronization as part of the operator, not an invisible correctness tax.

## Cost and rejection boundary

Volta does not inherit later mbarrier or cluster-shared machinery. Divergence/early exits must preserve arrival contracts. A polling loop without a visibility/progress proof is not a cheaper barrier. Compare phase granularity and pipeline depth.

## Next reads

Compositions: C19 C25. Experiments: E06 E15 E16.
