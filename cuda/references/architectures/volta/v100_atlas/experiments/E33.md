# E33 — Power and steady-state behavior

> Is the proposed schedule faster after thermal and power transients settle?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, power, and, steady-state, behavior.
**Prerequisites:** R12. **Evidence:** S02 S36.

**Question:** Is the proposed schedule faster after thermal and power transients settle?

**Minimal setup:** Run equal-work schedules to stable conditions under unchanged supported limits; record clocks, temperature, power and useful outputs.

**Sweep:** Overlap ratio, phase order, neighbor activity and workload duration.

**Discriminating observation:** Sustained throughput and energy per result with raw telemetry context.

**Baseline:** Maximum-overlap and simple fixed schedules.

**Confounders / correctness:** Sensor averaging, ambient changes and reduced precision/work can manufacture apparent gains.

**Access gate:** No voltage/firmware modifications or unsafe power-limit changes.

**Related:** C33 M52.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
