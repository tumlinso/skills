# M21 — L2 as a compact coordination service

> A large computation can have a very small shared control state.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** L2, atomics, coordination.
**Prerequisites:** R03 R06. **Evidence:** S02 S04 S30.

## Established substrate [D/E + H composition; reachability C/P]

L2 and global atomic handling participate in the device-wide memory hierarchy. Exact latency, address hashing and residency remain implementation/measurement questions. Later persistence controls are not assumed.

## Appropriation hypothesis

Keep queue heads, ownership words or support masks compact; aggregate locally before touching global state. Shard independent counters to reduce contention. Atomic OR/min/max can embody a merge algebra for suitable dataflow.

## Cost and rejection boundary

One hot address can serialize the algorithm despite large total bandwidth. False sharing, polling and fences matter. Do not rely on cache residency or infer peer coherence from local atomic success. Measure useful successful updates rather than raw attempts.

## Next reads

Compositions: C24 C25. Experiments: E07 E14 E18.
