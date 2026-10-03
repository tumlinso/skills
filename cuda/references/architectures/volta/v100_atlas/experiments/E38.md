# E38 — Negative-space falsification

> Which attractive interpretation is actually unsupported or algebraically wrong?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, negative-space, falsification.
**Prerequisites:** R12. **Evidence:** S03 S12 S27 S30.

**Question:** Which attractive interpretation is actually unsupported or algebraically wrong?

**Minimal setup:** Write the required primitive/contract, then check exact target/form, interface and algebra before any performance experiment.

**Sweep:** Claims such as partial-warp MMA, DMA array reduction, automatic peer coherence or generic semiring MMA.

**Discriminating observation:** A minimal contradiction or missing-contract statement attached to the rejected idea.

**Baseline:** A supported equivalent with explicit software work.

**Confounders / correctness:** Failure of one interface does not prove silicon impossibility; header presence does not prove usability.

**Access gate:** No malformed opcode/command execution merely to see whether it crashes.

**Related:** R00 R04 R09 C39.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
