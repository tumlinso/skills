# E32 — Launch, graphs and CDP

> Which supported submission mechanism best matches task granularity?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, launch, graphs, and, cdp.
**Prerequisites:** R12. **Evidence:** S30 S32 S06.

**Question:** Which supported submission mechanism best matches task granularity?

**Minimal setup:** Compare finite equivalent stages through host launches, instantiated graphs and supported device-side launch variants.

**Sweep:** Task size, repetition, parameter updates and dependency structure.

**Discriminating observation:** Host overhead, device idle gaps and total completion time.

**Baseline:** Properly batched launches with minimized unnecessary synchronization.

**Confounders / correctness:** Device-side launch is not a remote launch; modern graph/CDP features need exact target/version verification.

**Access gate:** Installed compatible APIs and per-device cooperative checks.

**Related:** M32 M33 C25 C28.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
