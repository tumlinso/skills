# E30 — Binary transformation validation

> Does an edited cubin preserve semantics and improve the intended bottleneck?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, binary, transformation, validation.
**Prerequisites:** R12. **Evidence:** S04 S05 S11.

**Question:** Does an edited cubin preserve semantics and improve the intended bottleneck?

**Minimal setup:** Pin compiler/tool/architecture and hash original/edited binaries. Validate metadata, relocations, def/use and dependency controls before differential execution.

**Sweep:** Boundary inputs, resource pressure, memory latency and compiler baseline variants.

**Discriminating observation:** Exact or bounded outputs plus isolated and full-kernel performance evidence.

**Baseline:** Original ptxas output and source-level alternatives.

**Confounders / correctness:** A transformation can pass warm-cache tests yet fail under variable latency; random tests alone do not establish legality.

**Access gate:** B-level edits isolated to controlled experiments, not a claim of universal kernel rewriting.

**Related:** C17 C34 M48.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
