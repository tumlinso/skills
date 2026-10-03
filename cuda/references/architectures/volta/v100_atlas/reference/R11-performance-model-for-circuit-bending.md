# R11 — Performance model for circuit bending

> Compare complete semantic work, including conversions and synchronization.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** cost model, representation, break-even, optimization.
**Prerequisites:** none. **Evidence:** original synthesis; see linked mechanisms.


For representation R:

```
T(R)=Tencode+Tcritical_schedule+Tsynchronization+Tdecode
Tcritical_schedule >= max(dependency path, each shared-resource demand/service rate)
```

This is a lower bound, not a simulator. Different execution pipes can share issue slots, register ports, cache/memory and power. Sum of peak rates is not a realizable machine model. An interleaved kernel only helps if it performs work the application actually needs.

A representation wins after reuse n when n·per_use_saving > encode+decode+maintenance. A bitset maintained every step has different economics from immutable support. A fragment retained across ten operators has different economics from one expanded binary matrix product.

Latency hiding needs enough independent chains and request concurrency. More occupancy can increase independence but reduce locality or force smaller tiles. A large register circuit can be efficient with fewer warps when it has internal ILP; it can fail badly if it is one long dependency chain. Measure eligible work, not merely resident threads.

For communication, compare startup+payload/B+local work for direct pull, bulk stage and owner-compute. Queue/publication/response belongs in startup, not an omitted detail. Owner-compute is attractive when it reduces information crossing the boundary enough to repay service overhead.

For sparse versus dense, track useful tile work U/issued work W. Sparse paths pay metadata/gathers/control; dense paths pay zeros/padding/conversion. Density alone is not a decision rule. The operator's reuse and native representation determine the crossover.

Dynamic adaptation needs a remaining-horizon estimate and hysteresis. Switch only if expected future saving repays observation, repacking, cold state and uncertainty. A sophisticated profiler-backed policy can lose to a cheap density heuristic.

A reusable performance claim names semantic operation, in put distribution, output contract, baseline, preprocessing reuse, numerical error, bytes, instruction mix, clocks, repetitions, median/tails and raw results. An isolated “2×” is not architecture knowledge. Record failures just as precisely.
