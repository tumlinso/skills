# E13 — Representation crossover

> How many uses repay bitplanes, packing or a changed numerical domain?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, representation, crossover.
**Prerequisites:** R12. **Evidence:** S08 S09 S03.

**Question:** How many uses repay bitplanes, packing or a changed numerical domain?

**Minimal setup:** Implement encoding, steady-state operators and decoding as separately timed stages plus a complete path.

**Sweep:** Reuse count, state cardinality, update rate, partial groups and data distribution.

**Discriminating observation:** A measured break-even model that predicts held-out cases.

**Baseline:** Best direct representation including existing packed or vectorized alternatives.

**Confounders / correctness:** Omitting maintenance or final decoding creates fictional wins; scalar versus packed output contracts differ.

**Access gate:** Run CPU identity checks first; inspect sm70 lowering for packed intrinsics.

**Related:** C00 C01 C02 C07 C08 C09 C37.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
