# E01 — Algebra and encoding checks

> Are the proposed word circuits and layout equations actually equivalent?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, algebra, and, encoding, checks.
**Prerequisites:** R12. **Evidence:** original synthesis; see linked mechanisms.

**Question:** Are the proposed word circuits and layout equations actually equivalent?

**Minimal setup:** Run tools/semantic_checks.py. Extend with exhaustive small truth tables and deterministic randomized references for any new composition.

**Sweep:** Partial groups, widths, boundary symbols, overflow guards and all small finite states.

**Discriminating observation:** Exact agreement for Boolean/routing identities and deliberate failure of insufficient-guard negative controls.

**Baseline:** Simple integer/list reference implementations.

**Confounders / correctness:** CPU success does not test GPU rounding, collective participation, compiler lowering or memory ordering.

**Access gate:** CPU only; the supplied suite is actually run and logged in this package.

**Related:** C00 C01 C02 C03 C05 C06 C07 C37.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
