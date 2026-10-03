# E27 — Copy remap reachability

> Can the declared component transformer be safely invoked and outperform SM formatting?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, copy, remap, reachability.
**Prerequisites:** R12. **Evidence:** S12 S15.

**Question:** Can the declared component transformer be safely invoked and outperform SM formatting?

**Minimal setup:** Before any command, establish an owned driver/channel implementation and exact descriptor rules. Begin with tiny fixed records and a CPU reference.

**Sweep:** Expressible component selections, constants, widths, pitches and transfer sizes.

**Discriminating observation:** Correct transformation and full cost versus public copy plus/fused shader transform.

**Baseline:** Public memcpy and optimized SM conversion.

**Confounders / correctness:** Header fields do not provide complete ownership/format/lifetime semantics. No arbitrary gather assumed.

**Access gate:** K-level, NOT executable from the package; requires separate privileged engineering and recovery plan.

**Related:** C26 M37 R09.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
