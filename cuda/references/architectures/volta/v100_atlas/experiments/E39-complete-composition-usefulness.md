# E39 — Complete composition usefulness

> Does the new representation improve the actual problem after all costs?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, complete, composition, usefulness.
**Prerequisites:** R12. **Evidence:** original synthesis; see linked mechanisms.

**Question:** Does the new representation improve the actual problem after all costs?

**Minimal setup:** Implement equal semantic workloads for a strong conventional, representation-changing and alternate-resource candidate.

**Sweep:** Shape, sparsity, distribution, reuse, accuracy and topology, including held-out cases.

**Discriminating observation:** End-to-end time/tails, memory use, energy and validity with a explainable crossover.

**Baseline:** Best applicable existing algorithm, not a straw-man scalar implementation.

**Confounders / correctness:** Preprocessing, maintenance, decoding, synchronization and output contracts must be included.

**Access gate:** All relevant correctness/capability tests passed; retain negative results.

**Related:** C39 R11 R15.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
