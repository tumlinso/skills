# E28 — Copy-engine semaphore actor

> Can completion-word operations replace a shader boundary in a real pipeline?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
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
