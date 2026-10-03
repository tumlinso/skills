# E26 — Texture and SFU approximation

> Can a specialized arithmetic path meet a useful error/performance contract?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, texture, and, sfu, approximation.
**Prerequisites:** R12. **Evidence:** S30 S03.

**Question:** Can a specialized arithmetic path meet a useful error/performance contract?

**Minimal setup:** Compare table/interpolation, SFU seed/refinement and polynomial implementations over a bounded domain.

**Sweep:** Table spacing, formats, coordinate boundaries, derivative extremes and exceptional values.

**Discriminating observation:** Worst-case error and complete execution cost at equal accepted tolerance.

**Baseline:** Conventional function implementation and cached table/manual interpolation.

**Confounders / correctness:** Ideal interpolation error omits hardware coordinate/filter/sample precision. Random tests miss extrema.

**Access gate:** Documented Tesla CUDA texture/SFU path only; no assumed inaccessible graphics engine.

**Related:** C31 M10 M23.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
