# E29 — Dependent QMD minimal experiment

> Is there a usable restricted descriptor dependency beyond public graph execution?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, dependent, qmd, minimal, experiment.
**Prerequisites:** R12. **Evidence:** S27 S13 S40.

**Question:** Is there a usable restricted descriptor dependency beyond public graph execution?

**Minimal setup:** First resolve ownership, units, reference counts, cache visibility and completion from implementation evidence. Only then consider two finite known kernels.

**Sweep:** A single dependency/release relation before any circular or dynamic structure.

**Discriminating observation:** Correct bounded execution and total cost versus graph replay.

**Baseline:** Public instantiated graphs and batched launches.

**Confounders / correctness:** Descriptor fields alone do not prove arbitrary graph semantics or SM affinity. No self-modifying live descriptors.

**Access gate:** S/K frontier; no executable low-level command generator supplied.

**Related:** C28 M39 R09.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
