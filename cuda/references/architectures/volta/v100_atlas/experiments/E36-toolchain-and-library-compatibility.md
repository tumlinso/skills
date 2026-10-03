# E36 — Toolchain and library compatibility

> Which installed artifacts actually execute native sm70 paths?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, toolchain, and, library, compatibility.
**Prerequisites:** R12. **Evidence:** S06 S05 S32 S41.

**Question:** Which installed artifacts actually execute native sm70 paths?

**Minimal setup:** Compile a tiny native sm70 kernel with the intended toolchain; inspect cubin/fatbin and record driver/library build paths.

**Sweep:** Compiler versions, PTX/cubin selection and required library operators.

**Discriminating observation:** A per-feature compatibility matrix rather than a blanket CUDA-version claim.

**Baseline:** A preserved known-working sm70 toolchain and native binary.

**Confounders / correctness:** New driver API spelling does not imply a new hardware feature; management displayed version is not compiler version.

**Access gate:** No assumption that latest library releases retain Volta support.

**Related:** R10 M45 M48.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
