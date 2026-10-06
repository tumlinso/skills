# E27 — Copy remap reachability

> Can the declared component transformer be safely invoked and outperform SM formatting?

**Status:** NOT_RUN (subset: restricted original component-transformer hypothesis). **Original protocol status:** NOT_RUN_ON_GPU ([archived E27 at commit 5c1f805db80a](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E27.md)). **Depth:** 4.
**Read when:** experiment, copy, remap, reachability.
**Prerequisites:** R12. **Evidence:** S12 S15.

**Question:** Can the declared component transformer be safely invoked and outperform SM formatting?

**Minimal setup:** Before any command, establish an owned driver/channel implementation and exact descriptor rules. Begin with tiny fixed records and a CPU reference.

**Sweep:** Expressible component selections, constants, widths, pitches and transfer sizes.

**Discriminating observation:** Correct transformation and full cost versus public copy plus/fused shader transform.

**Baseline:** Public memcpy and optimized SM conversion.

**Confounders / correctness:** Header fields do not provide complete ownership/format/lifetime semantics. No arbitrary gather assumed.

**Access gate:** K-level, NOT executable from the package; requires separate privileged engineering and recovery plan.

**Related:** C26 M37 R09.

**Record:** UUID/SKU; topology; compiler/driver/flags/cubin hash; memory type; clocks/power/temperature; launch shape; raw samples; repetitions; median/tails; numerical contract; profiler/replay mode. Unknown measurements are null, never zero. See R12 and result.schema.json.

## Measured coverage (2026-10-06)

The final campaign record reports 0 cases and no correctness result for E27. The protocol’s proposed component-transformer path was not executed. The nearby public copy and shader-conversion cases do not invoke that transformer.

Primary scope: no implementation of the declared privileged transformer was exercised. The adjacent [public peer-copy path in run_e20](../benchmarks/native/transport.cu#L772) does not test component remapping.

[Measured summary](evidence/v100-20261006/E27.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- **Supports:** this campaign provides no observation about component-transformer reachability, correctness, or speed.
- **Design implication (inference):** first establish descriptor ownership, component-selection rules, and the record/layout contract, then compare full transfer cost against the protocol’s public-copy and shader-transform baselines.
- **Does not establish:** arbitrary gather support, safety, or a performance advantage for the restricted transformer.
- **Original protocol gaps:** no component selection, constant, width, pitch, transfer-size sweep, CPU reference, or owned-driver implementation ran.
