# E04 — Register bank and operand-reuse effects

> Does operand delivery limit this hot sequence?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, register, bank, and, operand-reuse, effects.
**Prerequisites:** R12. **Evidence:** S04 S05 S11.

**Question:** Does operand delivery limit this hot sequence?

**Minimal setup:** Compare semantically identical schedules with controlled operand assignment/reuse. Preserve original cubin and exact transformation.

**Sweep:** Register parity, source reuse, inserted amortized copies and independent instruction spacing.

**Discriminating observation:** Repeatable changes tied to distinct bank reads rather than occupancy or arithmetic changes.

**Baseline:** Original compiler output and a dependency-matched schedule.

**Confounders / correctness:** Changed live ranges, spills, resource metadata and clock state. Source names do not identify physical registers.

**Access gate:** B-level edits require validated tools and complete dependency/resource preservation.

**Related:** C17 M12 M13.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
