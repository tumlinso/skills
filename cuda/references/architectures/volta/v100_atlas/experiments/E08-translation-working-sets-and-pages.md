# E08 — Translation working sets and pages

> Is the irregular workload limited by translation rather than data bandwidth?

**Status:** NOT_RUN_ON_GPU. **Depth:** 4.
**Read when:** experiment, translation, working, sets, and, pages.
**Prerequisites:** R12. **Evidence:** S04 S16 S31.

**Question:** Is the irregular workload limited by translation rather than data bandwidth?

**Minimal setup:** Hold useful bytes constant while changing page footprint and traversal order. Record VMM allocation settings separately from observed translation behavior.

**Sweep:** Page count, stride, allocation method, reuse and concurrent requests.

**Discriminating observation:** Performance changes with translation footprint that remain after data-cache controls.

**Baseline:** Page-local traversal and conventional contiguous allocation.

**Confounders / correctness:** VMM granularity is not automatically TLB page size; VA patterns do not directly reveal physical channel bits.

**Access gate:** Only supported allocation/advice/VMM interfaces; no direct PTE modification.

**Related:** R08 M40 C38.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.
