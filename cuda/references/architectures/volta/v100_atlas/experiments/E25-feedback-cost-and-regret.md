# E25 — Feedback cost and regret

> Does adaptation outperform a fixed policy after paying for observation and switching?

**Status:** GPU_RUN (implemented subset only; see measured coverage). **Original protocol status:** NOT_RUN_ON_GPU ([immutable original card](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E25.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

Eight correctness-valid GPU cases evaluate fixed serial, fixed parallel, adaptive pilot, and offline oracle policies over eight known alternating small/full phases, at two selected sizes and 30 repetitions. Both kernels compute output[i] = input[i] + 3. The host timing includes launch, event polling, and host scheduling. Across the two selected sizes, fixed-serial total medians are 2.398 and 4.532 ms; fixed-parallel medians are 2.357 and 2.388 ms. Adaptive-pilot observation medians are 18.421 and 18.114 ms, with total policy-cost medians 18.699 and 18.312 ms. Offline-oracle total medians are 0.276 and 0.274 ms, excluding candidate calibration cost by construction.

[Measured summary](evidence/v100-20261006/E25.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md) · [sync.cu: phase_serial_grid and phase_parallel_grid](../benchmarks/native/sync.cu#L157)

## Meaning through representation and execution

- **Supports:** A bounded comparison of execution and observation cost under the known synthetic phase schedule; in these cases, adaptive observation dominates total cost.
- **Design implication (inference):** A policy needs enough remaining work or expected savings to repay the time spent measuring candidates and switching.
- **Does not establish:** An online policy win or general regret result. The offline oracle is an in-sample lower bound with zero runtime calibration cost, not an independent held-out policy.
- **Original protocol gaps:** Unknown phase schedules, observation frequency, hysteresis, noise sensitivity, and representative switching/repacking costs remain untested.
