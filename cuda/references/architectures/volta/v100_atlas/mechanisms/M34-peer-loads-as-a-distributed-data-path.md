# M34 — Peer loads as a distributed data path

> Direct access is one option alongside compact owner answers and staging.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** NVLink, remote memory, graphs.
**Prerequisites:** R07 R06. **Evidence:** S02 S25 S30.

## Established substrate [A/D conditional; reachability C/P]

Supported peer mappings let a GPU address another GPU allocation. NVLink can carry those transactions. Exact caching, packetization and routing behavior is not fully implied by pointer accessibility.

## Appropriation hypothesis

Keep immutable tables or cold metadata at an owner and pull selected fields. Coalesce requester lanes. For high work per byte, send a compact query to a resident owner service and return a reduced result. Choose by reuse and information volume.

## Cost and rejection boundary

Remote memory is not uniform latency local HBM. Many dependent loads may lose to a staged tile. Verify permissions, scope and atomic support separately. Do not make correctness depend on an unverified local/remote cache path.

## Next reads

Compositions: C20 C21 C23. Experiments: E18 E19 E20.
