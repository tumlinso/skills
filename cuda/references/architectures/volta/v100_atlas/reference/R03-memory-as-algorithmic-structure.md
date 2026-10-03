# R03 — Memory as algorithmic structure

> Track useful information per transaction, translation footprint and reuse lifetime.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** memory, HBM, L1, L2, TLB, shared.
**Prerequisites:** none. **Evidence:** S01 S04 S16 S30 S31.


For each access family record useful bytes U, transferred bytes X, request count Q, physical owner, reuse interval, alignment and translation working set. U/X can explain a graph traversal better than achieved G B/s. A metadata-heavy workload may be limited by issue or translations while HBM utilization looks low.

Partition data by role: hot support/routing metadata; evolving local state; streaming payload; cold exceptional state. These roles can justify different representations and paths. A producer that emits the consumer's native layout can remove an entire gather/transpose, not merely make it faster.

Shared memory gives explicit placement and phase synchronization; caches provide policy/replacement behavior. A same-word broadcast and different words in the same bank are not equivalent. Bank conflicts are not a contractual arbitration mechanism. XOR swizzles or padding must be evaluated through the next consumer too.

Shared carveout, cache capacity and spills interact. A few deliberate cold spills can buy enough independent work to win; uncontrolled hot accumulator spills usually have a different cost. Compare total local-memory traffic, live state and end-to-end time. L2 can hold compact coordination data, but arbitrary line residency is not guaranteed and later persistence controls are not a Volta assumption.

Cache operators do not establish happens-before. Read-only/texture paths are not automatically coherent aliases for writable data. The exact requester/owner cache behavior of peer traffic remains a path-specific experiment. This atlas does not adopt a blanket claim that all remote loads are cached in the requester'sL2.

Translation is a second working set. Reordering by page can help even when data-cache hit rate barely moves. VMM allocation granularity is not automatically the actual TLB page size. Physical address hashes cannot be inferred universally from one virtual buffer.

To sustain bandwidth B with latency L and request payload s, roughly B·L/s outstanding payloads are needed before other limits. A single pointer chain therefore cannot exploit a wide link. Sometimes the winning transformation is to expose independent requests or send a compact query to an owner, rather than tuning the load instruction.
