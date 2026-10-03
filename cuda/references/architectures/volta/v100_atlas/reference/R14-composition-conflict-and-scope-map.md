# R14 — Composition, conflict and scope map

> Independent mechanisms often meet again at a shared bottleneck.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** composition, concurrency, scope, granularity.
**Prerequisites:** none. **Evidence:** S01 S12 S15 S25 S26 S30.


| Pair | Potential overlap | Shared limit to test |
|---|---|---|
|INT metadata +FP32|execution paths|issue, registers, dependencies|
|Tensor +prefetch|arithmetic vs outstanding loads|live registers, LDST, HBM, barriers|
|Tensor +conversion|independent instructions|conversion throughput, fragment routing|
|DMA +SM compute|different actors|HBM, fabric, power|
|Peer reads +local arithmetic|remote service|request slots, owner HBM, requester issue|
|Two transfer directions|possible engines/paths|engine assignment, roots, HBM|
|Atomic queues +bulk data|control vs payload|hot addresses, L2partitions, fences|
|MPS clients|independent work admission|resources, contention, fatal fault domain|

This is an experiment matrix, not a table of simultaneous peaks. E03/E17 establish the actual interference.

Scope hierarchy: register→thread; shuffle/vote→participating warp; shared/barrier→CTA; global atomics→specified scope; peer operations→supported pair; host mapped→system path; command completion→stream/channel/engine contract; firmware→privileged platform. An abstraction name does not widen scope.

Granularity hierarchy: bit, byte/half, word, lane, warp, MMA tile, shared bank, transaction/sector, page, DMA command, link packet, epoch. The semantic unit need not be identical at every level. A support mask can describe many edges while a tensor tile processes only a dense neighborhood.

Boundaries: ordinary CUDA does not distribute one warp/CTA across separate V100s; peer addresses do not name remote shared memory; VMM does not aggregateS Ms; MPS does not combine GPUs; smid observation does not grant affinity. These constrain mechanisms, not the possibility of useful software composition.

A useful algorithm makes its control, payload and ownership boundaries explicit. Shared resource conflicts should influence scheduling and layout; undocumented location/hash assumptions must remain performance hints rather than correctness dependencies.
