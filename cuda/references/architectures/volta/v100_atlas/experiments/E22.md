# E22 — Stream memory operations

> Which wait/write semantics are reachable and useful on the installed stack?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, stream, memory, operations.
**Prerequisites:** R12. **Evidence:** S17 S42.

**Question:** Which wait/write semantics are reachable and useful on the installed stack?

**Minimal setup:** Query capabilities; test finite value handshakes with explicit CUDA-visible ordering and non-managed supported memory.

**Sweep:** 32/64-bit width, comparison mode, batch size, remote flush support and wrap bounds.

**Discriminating observation:** Correct completion and measured full pipeline cost versus shader/event alternatives.

**Baseline:** Events and a tiny bounded polling/update kernel.

**Confounders / correctness:** Memory dependencies can be invisible to CUDA scheduling. GEQ wrap semantics are not ordinary unbounded integer comparison.

**Access gate:** S17/S42 restrictions must be satisfied before submission.

**Related:** C22 C27 M31.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
