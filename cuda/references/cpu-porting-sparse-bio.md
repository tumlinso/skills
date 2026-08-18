# CPU-To-CUDA Porting For Sparse Bioinformatics Code

Use this file when the code started life as CPU-centric sparse scientific code and now needs a GPU-shaped rewrite.

This is common for:

- row-wise QC loops
- feature-wise statistics
- thresholding and filtering
- remapping and compaction
- irregular sparse traversals
- sparse × dense projection
- metadata-heavy sparse pipelines

## Core Rule

Do not copy the CPU sparse loop structure literally.

First choose:

- the dominant sparse layout
- the sparse-to-dense boundary
- whether the work wants row bins, feature-wise transpose, or explicit sparse primitives

Only after that should you decide the CUDA kernel structure.

## 1. Common Bad Ports

- nested CPU loops over CSR with serial filtering folded into the same control flow
- preserving callback-heavy row processing
- keeping CSR for feature-heavy phases that clearly want CSC
- translating repeated SpMV-style loops instead of using SpMM
- porting serial filter-remap-writeout stages literally instead of compacting and staging on-device

## 2. Better GPU Rewrite Patterns

- row-wise work -> CSR plus row bins
- repeated feature-wise work -> build CSC once
- sparse × dense projection -> SpMM or fused equivalent
- filter/remap/writeout -> predicate plus compaction, then materialize
- mixed heavy/light rows -> bin or specialize before tuning

## 3. Tensor Core And Blocked Sparse Boundary

Do not chase Tensor Cores on raw sparse counts by default.

But if the sparse structure is genuinely block-stable and the end-to-end path is really a blocked sparse SpMM, explicitly compare against blocked ELLPACK-style storage before assuming CSR, CSC, or generic BSR is the right porting target.

## 4. Library First, Then Custom

Use explicit primitives first:

- cuSPARSE for primitive-shaped sparse math
- CUB for scan, segmented reduction, and compaction
- cuBLAS or cuBLASLt after the problem becomes dense enough

Escalate to custom kernels when the real cost is the glue:

- row-skew handling
- filtering plus remap
- metadata-heavy sparse bookkeeping
- launch-heavy multi-pass sparse preprocessing

## 5. Follow-On References

- `references/addendum-bio-data-layouts.md`
- `references/v100_bioinformatics_guide.md`
- `references/addendum-kernel-mechanics.md`
- `references/addendum-tensor-core-routing.md` when blocked sparse SpMM is the real target
