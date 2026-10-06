# E28 — Copy-engine semaphore actor

> Can completion-word operations replace a shader boundary in a real pipeline?

**Status:** NOT_RUN (subset: restricted original semaphore-actor hypothesis). **Original protocol status:** NOT_RUN_ON_GPU ([archived E28 at commit 5c1f805db80a](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E28.md)). **Depth:** 4.
**Read when:** experiment, copy-engine, semaphore, actor.
**Prerequisites:** R12. **Evidence:** S12 S15 S17.

**Question:** Can completion-word operations replace a shader boundary in a real pipeline?

**Minimal setup:** Establish a valid command route from pinned HAL evidence. Test release, increment and timestamp separately on isolated owned control storage.

**Sweep:** Counter values, INC/DEC threshold/wrap rules, flush modes and command sequencing.

**Discriminating observation:** Exact word semantics and complete pipeline latency without payload transfer.

**Baseline:** Public stream memory operations, events and tiny kernels.

**Confounders / correctness:** Reduction is on a semaphore word, not array data. Clocks and visibility domains must not be conflated.

**Access gate:** K-level until a safe public equivalent is used; no live CUDA-owned pushbuffer patching.

**Related:** C27 M38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.

## Measured coverage (2026-10-06)

The final campaign record reports 0 cases and no correctness result for E28. No low-level completion-word command route was exercised. The E32 launch/graph/CDP pipeline uses public submission mechanisms and does not test semaphore-word release, increment, threshold, flush, or visibility semantics.

Primary scope: no semaphore-actor implementation was exercised. The adjacent [public E32 submission variants in run_e32](../benchmarks/native/transport.cu#L938) are not copy-engine completion-word operations.

[Measured summary](evidence/v100-20261006/E28.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- **Supports:** no result here addresses the E28 completion-word question.
- **Design implication (inference):** an eventual test must define the semaphore word’s ownership, ordering, visibility, wrap/threshold behavior, and completion contract before comparing full-pipeline latency.
- **Does not establish:** payload-array reduction by a copy engine or replacement of a shader boundary.
- **Original protocol gaps:** release/increment/timestamp operations, counter values, flush modes, command sequencing, and comparison against stream operations/events/tiny kernels were not tested.
