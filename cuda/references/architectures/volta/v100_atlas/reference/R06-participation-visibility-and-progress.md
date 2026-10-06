# R06 — Participation, visibility and progress

> Every unconventional executor needs all three proofs; a faster flag is not a complete protocol.

**Status:** source-backed synthesis. **Depth:** 1.
**Read when:** synchronization, queues, atomics, correctness.
**Prerequisites:** none. **Evidence:** S03 S10 S17 S25 S30 S33.


**Participation:** all lanes named by a synchronized primitive must meet its contract. Capture logical membership before divergence. A selected shuffle source must participate and hold a defined value. A block barrier must have the intended arrivals; a warp mask cannot legalize a partial-warp MMA when the form requires the complete warp.

**Visibility:** atomicity, ordering, scope and cache visibility are different. Legacy atomic CAS/Add is not a general publication fence. A release flag protects preceding payload writes only when the reader's matching acquire and buffer lifetime are correct. Cache hints and volatile do not repair data races. Peer/GPU/CPU/external-DMA paths have different contracts; use the actual supported memory type and scope.

**Progress:** independent-thread scheduling is not arbitrary fairness. Streams may serialize. Busy consumers can occupy all resources needed by a producer. Cooperative grid synchronization needs supported admission/residency. A spin barrier in an oversubscribed ordinary grid can deadlock. MPS resource fractions do not prove a blocked producer can run.

The stream-memory API warns that dependencies expressed only through values are invisible to CUDA scheduling. The memory-level dependency graph and CUDA-visible event graph must be considered together. A correct value comparison can still sit in a deadlocked submission graph.

A queue protocol needs slot ownership, reservation, publication, reuse, sequence/epoch rules, wraparound bounds, cancellation, backpressure, stop/drain and peer-failure behavior. Reservation and publication are not the same event. An empty local queue is not distributed termination while messages or producers remain in flight.

Abstract SPSC publication pattern:

```
producer owns slot → writes payload → release-publishes epoch
consumer acquire-observes epoch → reads payload → release-publishes reuse
producer acquire-observes reuse before overwriting
```

This is a proof structure, not a promise that a particular atomic overload works on every peer/mapped-host allocation. Tests can find failures but cannot legalize an operation outside the documented memory model. Use finite bounded tests and preserve a schedulable termination path.
