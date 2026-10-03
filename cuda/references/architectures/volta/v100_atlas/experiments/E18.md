# E18 — Peer loads, cache behavior and latency

> What actually services repeated peer accesses on the tested path?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, peer, loads, cache, behavior, and, latency.
**Prerequisites:** R12. **Evidence:** S02 S25 S30.

**Question:** What actually services repeated peer accesses on the tested path?

**Minimal setup:** Use pointer chains and independent requests to peer allocations; compare read-only phases and correctly synchronized writes.

**Sweep:** Working set, stride, cache form, concurrency, allocation and owner-side traffic.

**Discriminating observation:** Signatures that separate startup, translation, caching and owner-memory contention.

**Baseline:** Local HBM and explicit peer staging.

**Confounders / correctness:** A latency reduction does not by itself prove requester L2 caching or coherent writable aliases.

**Access gate:** Validate peer capability and use legal ordering; no unsynchronized cache-coherence tests.

**Related:** R07 C20 M34.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
