# E25 — Feedback cost and regret

> Does adaptation outperform a fixed policy after paying for observation and switching?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, feedback, cost, and, regret.
**Prerequisites:** R12. **Evidence:** S34 S35 S36.

**Question:** Does adaptation outperform a fixed policy after paying for observation and switching?

**Minimal setup:** Use a small set of already-correct kernels and repeat workloads with known phase changes. Log policy decisions.

**Sweep:** Observation frequency, hysteresis, noise, remaining horizon and switch/repacking cost.

**Discriminating observation:** Total regret versus best fixed and offline phase-aware controls.

**Baseline:** Fixed policies and a cheap density/time heuristic.

**Confounders / correctness:** Profiler replay and thermal drift can change the workload being controlled.

**Access gate:** Only installed compatible observation APIs; keep an uninstrumented control.

**Related:** C32 C33 M46.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
