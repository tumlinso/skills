# Corrections and quarantined inferences

1. Full GV100 die resources are not identical to an enabled V100 SKU. Inventory the actual machine.
2. Six NVLink ports per GPU do not mean six ports to one peer. Bidirectional aggregate and one-way payload are different metrics.
3. VMM/UVA naming does not merge SM scheduling, cache coherence or physical latency.
4. Four m8n8k4 subproducts remain a full-warp collective. Eight logical participants do not authorize partial-warp execution.
5. Explicit PTX fragment maps do not license opaque WMMA layout assumptions.
6. Copy-engine semaphore reduction is not array reduction. A command field is not a public CUDA function.
7. Dependent QMD fields do not establish a programmable arbitrary task graph or ordinary CUDA SM affinity.
8. New PTX syntax can target old silicon. Conversely, a Volta-family mnemonic list can include forms not established on GV100/sm70. Integer WMMA sm72+ is not sm70 support.
9. Current NVIDIA open kernel modules do not support V100, despite useful Volta UVM source being published.
10. Complementary pipelines share issue, registers, memory and power; their peak throughputs cannot simply be added.
11. FP32 tensor accumulation is not a promise of arbitrary scalar IEEE FMA order. Numerical encodings need targeted validation and bounds.
12. SM/warp IDs are not automatically stable application identities. Cross-device timers are not assumed synchronized.
13. Independent-thread scheduling does not prove arbitrary spin-loop fairness or producer residency.
14. Pinning pages and pinning a host thread do not establish NUMA page locality. Removing an extra CPU copy does not remove PCIe DMA.
15. Cache hints and volatile do not repair publication races. Reservation does not mean payload completion.
16. A successful mapping/driver query does not establish remote cache policy or achieved bandwidth.
17. Public graph replay is a baseline for exotic command scheduling, not an abstraction to reject on philosophical grounds.
18. CPU algebra checks do not validate GPU code generation, hardware arithmetic rounding, ordering or speed.
