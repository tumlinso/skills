# E34 — RAS contamination audit

> Are performance or correctness observations confounded by hardware errors or recovery?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, ras, contamination, audit.
**Prerequisites:** R12. **Evidence:** S02 S28 S36.

**Question:** Are performance or correctness observations confounded by hardware errors or recovery?

**Minimal setup:** Read ECC, retired-page, link and management status before/after a normal finite benchmark.

**Sweep:** Normal repeated runs and existing health differences only.

**Discriminating observation:** Explicit exclusion/annotation of contaminated samples.

**Baseline:** Clean stable runs on the same device.

**Confounders / correctness:** Reset can involve NVLink peers; error absence in one log is not proof of perfect hardware.

**Access gate:** Read-only audit; no intentional ECC/link fault injection or routine resets.

**Related:** R13 M51.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
