# R07 — NVLink, PCIe and NUMA as information boundaries

> Compare pull, push, staging and owner computation on the actual directed topology.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** NVLink, PCIe, NUMA, communication.
**Prerequisites:** none. **Evidence:** S02 S25 S26 S30 S33 S36.


Inventory each ordered pair: direct links, peer-load permission, native atomic support, performance rank, DMA route and host roots. Six ports on one GPU does not mean six links to a chosen peer. Distinguish one-way payload, simultaneous two-way payload, unloaded latency and saturation. n direct links gives a physical directional ceiling n·25 GB/s before overhead, not a measured guarantee.

Three data modes deserve comparison. **Pull:** requester loads selected remote fields. **Push/owner-compute:** owner filters/reduces a large local structure and sends a small result. **Bulk stage:** copy a region then reuse locally. Each can win in a different sparsity/reuse/latency regime. A remote service is a software construction, not a hardware remote launch caused by a pointer dereference.

Remote requests consume owner-side memory resources. Concurrent local compute can therefore change their performance even if requester utilization is low. Read-only remote caching must be measured for the exact instruction/allocation/path; do not derive coherence from a cache-speed plateau.

Do not assume aGV100 transparently routes arbitrary traffic through another GPU. NVSwitch is a separate component. POWER9 CPU coherence/ATS is a platform feature, not a generic property of two V100L2 caches on an x86 host.

Two GPUs attached to different CPU sockets can provide two ingress paths if data production and pinned-page placement align. Pinning does not itself guarantee locality. Avoiding an extra CPU copy does not eliminate PCIe DMA. Actual roots, switches, ACS/IOMMU and CPU-interconnect routing need inventory rather than inference from slot layout.

The deeper optimization is often information reduction. A frontier mask or query result may be a better transfer unit than the original tensor. Conversely, a thousand dependent remote scalar loads can cost more than one explicit staged tile. C20–C23 compare these possibilities without selecting any meta-device abstraction.
