# C23 — Topology-aware ownership and dual host ingress

> Align where bytes are produced, stored and consumed instead of forcing one uniform path.

**Status:** original hypothesis; no local GPU measurement. **Depth:** 3.
**Read when:** NUMA, PCIe, NVLink, ownership.
**Prerequisites:** M43 M36 M34 R07. **Evidence:** S30 S33 S36.

## Construction [H; reachability C/P]


Discover actual directed paths and host roots. Partition produced data so CPU-local pinned pages feed the corresponding GPU owner. Place each hot operator near its dominant state and transfer reduced boundary information. Compare both ingress paths concurrently to isolated transfers.

A pair spanning NUMA nodes can have useful independent input capacity when the application can produce data locally. This is a workload/topology opportunity, not proof that every x8 pair behaves that way.


## Why it could work

The representation acquires a physical home, which can remove unnecessary cross-socket traffic and remote GPU loads. Different boundaries can use different units of work without a meta-device abstraction.

## Full cost and strongest baseline

Count producer relocation, page placement, PCIe DMA and CPU-interconnect traffic. Thread affinity alone does not prove page locality. Simultaneous paths may share hidden roots or HBM service.

## Falsifier / rejection condition

Reject when topology inventory disproves independence, when data is inherently produced on the other node, or when boundary traffic overwhelms the locality benefit.

**Experiment:** E20 E21 E35. This composition has not been benchmarked on a V100 here.
