# R12 — Measurement discipline and obs er v ability

> Use measurements to discriminate explanations, not merely collect impressive counters.

**Status:** source-backed synthesis. **Depth:** 2.
**Read when:** microbenchmarks, profiling, counters, validation.
**Prerequisites:** none. **Evidence:** S04 S34 S35 S36.


Separate host latency, stream-event intervals, device instruction timing, disassembly, resource counters and telemetry. They are different observers and clocks. Cross-device clock alignment is an experiment; do not subtract peer global timer values as if synchronized.

For dependence latency create a true chain and consume its result. For throughput use independent accumulators and account for loop/measurement overhead. For memory separate pointer chase from streams, warm from cold, local from peer, read from write. For atomics vary address contention and returned-value dependence independently.

A single latency plateau does not prove a cache level. Sweep working set, stride, concurrency, page policy and cache form. A measured address conflict is useful even when the physical hash remains unknown, but allocation dependence must remain explicit. Do not identify HBM bits solely from one CUDA VA range.

CUPTI tracing, callbacks, counters and sampling have different availability/overhead. Nsight Compute can replay kernels and alter cache/clock conditions. A replayed isolated kernel is not the same experiment as a live persistent multi-GPU pipeline. Keep uninstrumented end-to-end timing and diagnostic collection separate.

Runtime feedback may need only queue depth or epoch duration. A coarse controller can select among prevalidated representations while preserving a fixed-policy baseline. Include measurement cost, lag and noise in the policy objective.

Capture UUID/SKU, VBIOS, driver, compiler, flags, libraries, cubin hash, clocks, power, temperature, ECC, link state, NUMA, IOMMU, page policy, launch resources, profiler/replay and raw outputs. The forty E cards are test protocols, not forty implemented benchmarks. CPU algebra tests and a read-only capability probe are supplied separately; no GPU measurements are claimed.
