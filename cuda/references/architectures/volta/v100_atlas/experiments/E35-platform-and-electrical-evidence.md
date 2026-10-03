# E35 — Platform and electrical evidence

> Which module/baseboard details affect software-visible behavior?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, platform, and, electrical, evidence.
**Prerequisites:** R12. **Evidence:** S02 S36 S37 S39.

**Question:** Which module/baseboard details affect software-visible behavior?

**Minimal setup:** Collect exact SKU/part/VBIOS/BDF identifiers and available original platform documentation; inspect topology without physical modification.

**Sweep:** Device/OEM revisions, link widths, root placement and supported telemetry.

**Discriminating observation:** A source-backed platform matrix with explicit unresolved pins/rails/clock domains.

**Baseline:** Generic V100 assumptions, used only as hypotheses to check.

**Confounders / correctness:** SXM2 form factor does not prove identical wiring, firmware or enabled features.

**Access gate:** Read-only first; no probing unknown powered pins or firmware modifications.

**Related:** R13 R07 M49 M50.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
