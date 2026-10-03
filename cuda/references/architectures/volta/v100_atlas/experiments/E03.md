# E03 — Cross-pipeline interference

> Can two useful operation families overlap without saturating another shared resource?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, cross-pipeline, interference.
**Prerequisites:** R12. **Evidence:** S01 S04 S35.

**Question:** Can two useful operation families overlap without saturating another shared resource?

**Minimal setup:** Time each family alone, serially combined and interleaved at equal semantic work. Preserve enough independent operands to expose overlap.

**Sweep:** INT/FP/tensor/conversion/load mixes; relative work ratios; live-register budget.

**Discriminating observation:** Combined critical time closer to a maximum than a sum only where genuine overlap exists; counters explain new bottlenecks.

**Baseline:** Best isolated and serial schedules, not an intentionally poor ordering.

**Confounders / correctness:** Shared issue, register ports, HBM and power; extra work invalidates the comparison.

**Access gate:** Public/PTX forms; no unsupported later-architecture instructions.

**Related:** C18 C19 M16 R14.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
