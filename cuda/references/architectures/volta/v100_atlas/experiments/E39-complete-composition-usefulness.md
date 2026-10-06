# E39 — Complete composition usefulness

> Does the new representation improve the actual problem after all costs?

**Status:** GPU_RUN (subset: bounded repeated uint32 full-adder composition workload). **Original protocol status:** NOT_RUN_ON_GPU ([archived E39 at commit 5c1f805db80a](https://github.com/tumlinso/gpu_circuit_bending_atlas/blob/5c1f805db80a81f7476ede8292abba69821d104f/experiments/E39.md)). **Depth:** 4.
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

## Measured coverage (2026-10-06)

The semantic transition was `total = uint64(x) + uint64(b) + carry; x′ = low32(total); carry′ = high32(total)`, repeated for the selected reuse count with immutable `b`; correctness was checked against the 64-bit CPU oracle. The three variants were native arithmetic, bitplane encoding, and nibble-512 lookup. Sixty-six correctness-passing cases formed 22 matched size/reuse/pattern cells used sizes 1, 31, 32, 33, 1,023, 1,024, 65,536, and 1,048,576; reuse 1, 8, and 64; and selected random, alternating, and carry-heavy patterns (not the full Cartesian product). Each variant/cell had 30 complete-path samples. Full path included H2D, applicable variant computation (including bitplane encode/decode), synchronization, and D2H/materialization. Device allocation and nibble-table setup were excluded. Native generally had lower full-path medians. At size 65,536/reuse 8, bitplane was about 0.08% lower by median; the 95% unpaired 10,000-resample bootstrap interval for bitplane-minus-native difference was [−0.010072, 0.008283] ms and crosses zero.

Primary scope: [cpu_transition](../benchmarks/native/composition.cu#L193) defines the oracle; [run_composition](../benchmarks/native/composition.cu#L456) runs the variants and [run_case](../benchmarks/native/composition.cu#L260) measures resident and full-path phases.

[Measured summary](evidence/v100-20261006/E39.json) · [Full campaign](../archive/campaign/REPORT.source.txt) · [Interpretation guide](INTERPRETING_RESULTS.md)

## Meaning through representation and execution

- **Supports:** native generally led these matched full-adder cells; the one small bitplane median ordering at size 65,536/reuse 8 is not an established crossover because its interval crosses zero.
- **Design implication (inference):** representation choice depends on the semantic primitive and available parallelism: native arithmetic matches this carry chain, while a bitplane word packs 32 independent scalar instances (warp lanes process bit positions and shuffle planes), and bit masks can suit set-membership operations such as the separate E11 workload. These are distinct semantic units.
- **Does not establish:** energy, an end-to-end memory-use advantage, accuracy tradeoffs, topology dependence, or usefulness for workloads beyond these integer transitions; allocated workspaces were estimated but allocation cost was excluded.
- **Original protocol gaps:** boundary sizes 1/31/32/33/1,023/1,024 were included in the selected matrix, but no separately reserved holdout workload, application case, or generalization set is evidenced. No broad sparsity/distribution, accuracy, topology, or energy/memory sweep was performed. These results therefore do not establish broad composition usefulness.
