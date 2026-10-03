# E19 — Peer signaling and clock relationships

> How much does a complete GPU-to-GPU handshake cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, peer, signaling, and, clock, relationships.
**Prerequisites:** R12. **Evidence:** S03 S25 S30.

**Question:** How much does a complete GPU-to-GPU handshake cost?

**Minimal setup:** Use a finite epoch protocol with local send/receive intervals and separately estimate clock offset/drift through exchanges.

**Sweep:** Atomic versus event/command paths, polling cadence, message batch size and owner load.

**Discriminating observation:** Round-trip and tail latency plus explicit uncertainty for clock alignment.

**Baseline:** CUDA-visible event and staged communication protocols.

**Confounders / correctness:** Do not subtract raw timestamps from unsynchronized GPUs. Polling consumes fabric/cache service.

**Access gate:** Native peer operation support and a valid publication/progress proof.

**Related:** C20 C21 C22 M35 M47.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
