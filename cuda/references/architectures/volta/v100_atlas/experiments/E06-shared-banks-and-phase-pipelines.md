# E06 — Shared banks and phase pipelines

> Which layout and synchronization phase actually reduces complete movement cost?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, shared, banks, and, phase, pipelines.
**Prerequisites:** R12. **Evidence:** S01 S30.

**Question:** Which layout and synchronization phase actually reduces complete movement cost?

**Minimal setup:** Construct controlled broadcast/conflict patterns and producer-consumer tile stages. Keep the semantic data permutation fixed.

**Sweep:** Stride, swizzle, padding, payload width, barrier placement and shared carveout.

**Discriminating observation:** Producer-to-consumer timing and conflict behavior, not only a fast standalone store.

**Baseline:** Shuffles for small exchanges and conventional shared tiling.

**Confounders / correctness:** Same word broadcast differs from distinct words in one bank. All required participants must reach barriers.

**Access gate:** Public shared-memory/barrier contracts; no later mbarrier assumptions.

**Related:** C16 C19 C36 M18 M19.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
