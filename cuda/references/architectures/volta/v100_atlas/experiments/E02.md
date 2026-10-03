# E02 — Instruction latency versus throughput

> Which dependency and resource limits govern an exact sm70 instruction form?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, instruction, latency, versus, throughput.
**Prerequisites:** R12. **Evidence:** S01 S04 S05 S03.

**Question:** Which dependency and resource limits govern an exact sm70 instruction form?

**Minimal setup:** Create one true dependent chain and a separate multi-accumulator kernel. Consume results; inspect native SASS and subtract bounded measurement/loop overhead.

**Sweep:** Chain length, independent chains, warps, unrolling, operand forms and register pressure.

**Discriminating observation:** A serial latency estimate distinct from independent service throughput and saturation.

**Baseline:** Equivalent scalar operation and empty/loop controls.

**Confounders / correctness:** Compiler folding, clock changes, instruction-cache effects and added spills can masquerade as instruction latency.

**Access gate:** Public CUDA/PTX initially; B-level variants only after binary validation.

**Related:** R02 M16 M17 M47.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
