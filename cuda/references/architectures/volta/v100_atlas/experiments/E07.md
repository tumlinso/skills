# E07 — Cache and transaction accounting

> What fraction of traffic carries useful information, under which reuse conditions?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, cache, and, transaction, accounting.
**Prerequisites:** R12. **Evidence:** S04 S30 S35.

**Question:** What fraction of traffic carries useful information, under which reuse conditions?

**Minimal setup:** Use both independent streaming accesses and dependent pointer chains. Separate read/write, warm/cold and cache forms.

**Sweep:** Working set, stride, alignment, active lanes, concurrency and metadata/payload separation.

**Discriminating observation:** Latency/throughput/sector signatures consistent with a stated cache or transaction explanation.

**Baseline:** Contiguous useful-byte loads and a deliberately scattered control.

**Confounders / correctness:** TLBs, page allocation, compiler elimination and profiler cache flushing. A plateau alone does not prove a cache level.

**Access gate:** Public/PTX memory operations with legal cache semantics.

**Related:** R03 M20 M21 M22 C38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
