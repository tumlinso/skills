# E31 — MPS and process interference

> What sharing, latency and failure boundaries hold on this exact Volta stack?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, mps, and, process, interference.
**Prerequisites:** R12. **Evidence:** S01 S41 S30.

**Question:** What sharing, latency and failure boundaries hold on this exact Volta stack?

**Minimal setup:** Use compatible documented MPS/IPC configurations and benign finite workloads in separate clients.

**Sweep:** Client count, resource fractions, work mix and isolated versus shared execution.

**Discriminating observation:** Per-client tails, aggregate useful work and observed interference.

**Baseline:** Separate conventional contexts and single-client runs.

**Confounders / correctness:** Current MPS docs may include unsupported newer variants; resource shares do not prove fairness or fatal-fault isolation.

**Access gate:** No deliberate fault injection on shared hardware; preserve process/resource lifetimes.

**Related:** M45 C25.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
