# E11 — Tensor versus bitset intersections

> When do many shared overlap queries repay numeric expansion?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, tensor, versus, bitset, intersections.
**Prerequisites:** R12. **Evidence:** S19 S20 S08.

**Question:** When do many shared overlap queries repay numeric expansion?

**Minimal setup:** Compute identical intersection counts or threshold decisions with packed AND+POPC, DP4A and supported tensor tiles.

**Sweep:** Universe length, query count, reuse, density, tile padding and requested output sparsity.

**Discriminating observation:** Whole-operation crossover including encode/decode and numerical validation.

**Baseline:** Strong packed-bitset implementation with cached cardinalities.

**Confounders / correctness:** Computing a dense answer matrix that the application does not need is not equal useful work.

**Access gate:** Counts must pass E10 within a proved or conservatively validated bounded domain.

**Related:** C11 C14 M26.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
