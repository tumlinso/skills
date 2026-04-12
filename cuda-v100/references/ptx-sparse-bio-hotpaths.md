# PTX For Sparse Bioinformatics Hot Paths

Use this file only when PTX guidance was explicitly requested and the hotspot is a sparse or irregular bioinformatics kernel on Tesla V100.

This file is not about forcing PTX onto every omics kernel. It is about the narrow cases where control flow, masks, or sparse metadata handling are hot enough that PTX-level choices become relevant.

## Quick Map

- `1. Where PTX Helps In Bio Kernels`
- `2. Row-Skew And Work Classification`
- `3. Filtering And Compaction`
- `4. Thresholding, Masks, And QC`
- `5. Small Irregular Reductions`
- `6. Blocked Sparse Micro-Paths`
- `7. Anti-Patterns`

## 1. Where PTX Helps In Bio Kernels

PTX is most plausible for:

- masked filtering passes
- QC-style threshold checks
- compaction and remapping
- metadata-heavy sparse writeout
- row-skew helpers inside already-binned kernels
- tiny irregular reductions

PTX is usually not the first answer for:

- primitive-shaped SpMV or SpMM that cuSPARSE already handles well
- dense projection after the sparse-to-dense boundary
- large feature-wise phases that really want CSC or transpose
- kernels whose main problem is memory movement rather than control flow

## 2. Row-Skew And Work Classification

For sparse omics, heavy row skew is often the real cause of poor control flow.

Prefer this order:

1. bin rows by `nnz/row`
2. specialize the heavy and light cases
3. use PTX-level predicates only inside a stable bin when short branchy logic remains

Use PTX for row-skew only when:

- the binning policy is already good
- the remaining branchy logic is still hot
- the per-lane decisions are small enough that predication or select-style updates can help

Do not use PTX to hide a missing binning policy.

## 3. Filtering And Compaction

Filtering and writeout are strong PTX candidates when:

- many lanes fail a cheap predicate
- the surviving work is sparse
- lane-by-lane branching is hot

Good strategies:

- generate masks with predicate comparisons
- use ballots to identify surviving lanes
- compact survivors before doing heavier work
- keep the PTX-level control limited to the active-lane decision and writeout setup

If the compaction overhead exceeds the skipped work, keep the simpler branchy path.

## 4. Thresholding, Masks, And QC

Bioinformatics kernels often have short, repeated threshold logic:

- count thresholds
- QC flag updates
- mitochondrial or feature-group mask checks
- row/feature inclusion tests

These are PTX-friendly only when the guarded body is short.

Good use:

- predicate generation
- branchless select-style updates
- packing or tagging outputs without opening a longer branch region

Bad use:

- predicating long downstream memory-heavy work
- keeping many mutually exclusive expensive cases in one kernel

## 5. Small Irregular Reductions

For tiny irregular reductions:

- prefer warp shuffles and vote-driven active masks first
- use PTX-level predicates only to tighten the active set or remove short branch chains
- keep shared-memory use justified by real cross-warp reuse

If the reduction spans very different row classes, split or bin first.

## 6. Blocked Sparse Micro-Paths

Blocked sparse bio workloads can justify PTX when:

- the block structure is already stable
- the hot problem is metadata, masks, or short conditional handling around the block
- the Tensor Core route is not the right question

Use PTX here for:

- branch shaping
- predicate-driven metadata handling
- compact branchless selection in fixed micro-primitives

Do not confuse this with the Tensor Core blocked path. If the real win is dense tile math, route to the Tensor Core references instead.

## 7. Anti-Patterns

- applying PTX before deciding CSR versus CSC versus binned layouts
- using PTX to cover up a missing sparse-to-dense boundary decision
- hand-writing PTX for primitive-shaped sparse kernels that are better served by libraries
- predicating long heavy branches in QC or filtering pipelines instead of splitting the work

## 8. Follow-On References

- `references/addendum-bio-data-layouts.md`
- `references/v100_bioinformatics_guide.md`
- `references/addendum-kernel-mechanics.md`
- `references/ptx-general-guidelines.md`
