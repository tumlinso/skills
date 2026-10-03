# M40 — VMM views and virtual contiguity

> Change a view rather than moving bytes, when the exact mapping contract permits.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** VMM, alias, ring, layout.
**Prerequisites:** R08 R06. **Evidence:** S18 S31 S16.

## Established substrate [A/D conditional; reachability C Driver API]

VMM separates reservation, physical backing and permissions. Actual support and granularity must be queried. Naming one interval does not create uniform cost, coherence or one execution domain.

## Appropriation hypothesis

Investigate doubled virtual rings, shared immutable views and composite intervals. A legal alias can remove modulo/split window handling. A view can remove a descriptor layer without copying payload.

## Cost and rejection boundary

Confirm alias concurrency/cache contract and synchronize before backing changes. Mapping is per-phase, not assumed nanosecond dispatch. TLB pressure/granularity can outweigh saved address arithmetic. CPU alias intuition is not GPU evidence.

## Next reads

Compositions: C29 C30 C36. Experiments: E23 E08.
