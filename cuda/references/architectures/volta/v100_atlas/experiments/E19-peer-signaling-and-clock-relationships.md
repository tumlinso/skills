# E19 — Peer signaling and clock relationships

> How much does a complete GPU-to-GPU handshake cost?

**Status:** GPU_RUN (implemented subset only; see measured coverage). **Original protocol status:** NOT_RUN_ON_GPU ([immutable original card](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E19.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

Three correctness-valid GPU cases compare a 64-phase system-scope release/acquire peer-atomic handshake, a public cross-device event handshake, and a host-staged event handshake. CUDA-visible ordinals 0/1 bind in this run to physical GPUs 0/2. Complete-protocol medians are 0.335 ms for the peer atomic path, 0.0124 ms for the public event path, and 0.0142 ms for the host-staged event path. The measurement covers each full protocol; it does not subtract timestamps from the two GPU clocks.

[Measured summary](evidence/v100-20261006/E19.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md) · [transport.cu: peer_atomic_producer and peer_atomic_consumer](../benchmarks/native/transport.cu#L122)

## Meaning through representation and execution

- **Supports:** Correct completion for the selected finite ready/payload/ack protocol and comparison of its reported full-handshake time with the two event paths.
- **Design implication (inference):** For this workload and pair, the event paths impose less measured end-to-end handshake cost than the peer-system-atomic protocol.
- **Does not establish:** Primitive-only latency, cross-GPU clock alignment, or a universally faster path across message sizes, devices, or owner loads.
- **Original protocol gaps:** Poll cadence, message batching, clock offset/drift, and alternative native peer signaling were not swept.
