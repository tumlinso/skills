# M36 — Copy engines as asynchronous workers

> Exploit independent progress without forgetting shared HBM and power.

**Status:** established mechanism + unmeasured application hypothesis. **Depth:** 2.
**Read when:** DMA, copy, overlap, latency hiding.
**Prerequisites:** R09 R14. **Evidence:** S02 S12 S15 S30.

## Established substrate [A/D; reachability C; deeper K]

Transfer engines execute commands separately from shader arithmetic. Engine counts, paths and concurrency depend on actual device/driver. They still share memory/fabric resources withS Ms and peers.

## Appropriation hypothesis

Prefetch future tiles, evacuate results or maintain buffered stages while compute proceeds. Compare raw DMA to SM movement that fuses filtering or format conversion. The useful path depends on transformation, not just byte count.

## Cost and rejection boundary

Asynchronous API return does not prove hardware overlap. Small copies are command-dominated; more buffers consume capacity. A DMA engine is not an arbitrary vector ALU. Measure concurrent traffic and critical path, not only isolated G B/s.

## Next reads

Compositions: C19 C23 C26. Experiments: E17 E03.
