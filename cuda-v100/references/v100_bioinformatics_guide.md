# Extreme CUDA/C++ Optimization For Sparse Bioinformatics / Omics On Tesla V100 16GB

## Scope

Use this file for sparse biological matrices on V100:

- single-cell RNA-seq counts
- single-cell ATAC peak matrices
- spliced / unspliced velocity counts
- large cell×feature sparse matrices
- hybrid pipelines that stay sparse early and go dense later

This file is for CUDA/C++ implementation and optimization, not generic bioinformatics advice.

## Quick Map

- `1. Sparse Omics Reality On V100`
- `2. Master Layout Rule`
- `3. Data Representation Rules`
- `4. Library And Kernel Selection`
- `5. V100 Sparse-Kernel Doctrine`
- `6. Format Decisions`
- `7. High-Value Workload Patterns`
- `8. Row Binning And Long-Row Handling`
- `9. Multi-GPU Strategy On This Host`
- `10. Pipeline Template`
- `11. Anti-Patterns`

## 1. Sparse Omics Reality On V100

Sparse omics performance is usually dominated by:

- row-wise QC and normalization
- sparse × dense projection
- column statistics after transpose or reindexing
- filtering, compaction, and remapping
- gather / scatter glue
- row sharding with small global reductions

The true hot path is often not one big sparse primitive. It is the glue around a few primitives.

Assume throughout:

- CUDA 12.x on native `sm_70`
- PCIe is slow
- NVLink pair locality matters
- irregular `nnz/row` distributions are common
- memory traffic and load balance matter more than nominal FLOPs

## 2. Master Layout Rule

Choose the master sparse layout based on the dominant phase, not on convenience.

### 2.1 Use CSR As The Default When Work Is Cell-Wise

Keep rows = cells when the hot path is:

- row sums
- row normalization
- row filtering
- sparse × dense projection producing per-row outputs
- row sharding across GPUs

### 2.2 Build CSC When Work Becomes Feature-Wise

If the pipeline repeatedly needs:

- gene sums
- gene means / variances
- feature filtering
- column thresholding
- per-feature regression-like passes

build and reuse CSC or a transposed representation.

### 2.3 Practical Rule

- one or two feature-wise passes: maybe stay in CSR
- many feature-wise passes: build CSC once
- mixed row- and feature-heavy reuse: keep both CSR and CSC if memory and reuse justify it

The real question is not whether a phase can be forced through CSR. The real question is whether repeated column-oriented passes cost more than one transpose plus efficient column kernels.

## 3. Data Representation Rules

### 3.1 Indices

- keep indices 32-bit whenever possible
- coalesce duplicates early
- sort column indices within each CSR row if later kernels benefit

### 3.2 Values

- store values compactly
- accumulate reductions in FP32 when numerical stability matters

### 3.3 Pointer Qualifiers

Use `const __restrict__` aggressively on read-only inputs in custom kernels.

```cpp
__global__ void kernel(const int* __restrict__ rowptr,
                       const int* __restrict__ colind,
                       const float* __restrict__ vals,
                       float* __restrict__ out) {
  // ...
}
```

## 4. Library And Kernel Selection

### 4.1 Tier 1: Primitive-Shaped Sparse Work

Use first:

- cuSPARSE for SpMV, SpMM, SpGEMM, SDDMM, conversions
- CUB / CCCL for scans, segmented scans, segmented reductions, sorting, compaction

### 4.2 Tier 2: Dense Work After Reduction

Use:

- cuBLAS / cuBLASLt for dense projection, reduced-space GEMM, regression-like dense blocks
- cuSOLVER for SVD, eigendecomposition, or QR in reduced dense space
- cuVS for neighbor search after embeddings become dense enough

### 4.3 Tier 3: Custom Fused Kernels

Escalate aggressively when profiling shows the hot path is not primitive-shaped, especially for:

- row-binned sparse kernels
- fused normalization / threshold / transform passes
- filtering plus remapping plus writeout
- irregular gather / scatter bookkeeping
- format conversion plus immediate follow-on work
- glue work whose launch overhead dominates useful math

If the primitive is fast but the surrounding path is slow, optimize the full path.

## 5. V100 Sparse-Kernel Doctrine

### 5.1 Warp Rule

Use `_sync` intrinsics. Do not rely on old implicit warp lockstep.

### 5.2 Memory Rule

Sparse omics kernels on V100 are usually memory-bound. Prioritize:

- fewer global-memory passes
- better coalescing
- better row balance
- less launch overhead

Do not optimize sparse kernels as if peak occupancy were the primary target.

### 5.3 Row-Binning Rule

Bin rows by `nnz/row`. Fixed scheduling wastes warps when row lengths vary widely.

Good bins often look like:

- tiny rows
- short rows
- medium rows
- long rows

Map different bins to different kernels or execution strategies.

### 5.4 Atomics Rule

Avoid atomics unless:

- contention is naturally low
- the phase is small
- the simpler decomposition is already good enough in profiling

For heavy feature-wise aggregation, compare:

- transpose to CSC
- sort/group plus segmented reduction
- atomics only for low-contention tails

### 5.5 SpMM Rule

Prefer SpMM to repeated SpMV when the logical operation is sparse × dense projection.

## 6. Format Decisions

### CSR

Best for:

- row-wise work
- row sharding
- row reductions
- sparse × dense projection with per-row outputs

### CSC

Best for:

- repeated feature-wise passes
- column statistics
- repeated column filtering or thresholding

### COO

Use when assembly or intermediate construction is simpler in coordinate form, not as the default steady-state format.

### BSR

Use only when the block structure is real and stable enough to justify it.

### SELL / Sliced ELL

Useful when row lengths are regular enough after binning to justify a more structured layout.

## 7. High-Value Workload Patterns

### 7.1 Library Size / Total Count Per Cell

Use warp-per-row or row-binned row-sum kernels when CSR rows are the natural unit.

### 7.2 Row Normalization / Counts-Per-10k / log1p

This is one of the best fusion targets. Prefer a fused pass when it can combine:

- row sum reuse
- scaling
- thresholding
- optional transform like `log1p`

### 7.3 Gene-Wise Sums / Means / Variances

Bad default:

- repeated feature-wise passes through CSR with scattered atomics

Better options:

- build CSC once
- sort/group contributions and segmented reduce
- reserve atomics for small or low-contention phases

### 7.4 Sparse × Dense Projection

Prefer SpMM. Do not emulate projection with repeated SpMV if the dense RHS is naturally matrix-shaped.

### 7.5 PCA / Low-Rank Embedding

Stay sparse as long as the matrix is still huge and mostly zeros. Go dense after feature selection, aggregation, or projection shrinks the problem enough to make dense kernels dominant.

### 7.6 Neighborhood Graph Building

Once embeddings are dense enough, stop pretending this is still a sparse-kernel problem. Use dense-library or vector-search paths.

## 8. Row Binning And Long-Row Handling

### 8.1 Binning Policy

Use a bin policy driven by `nnz/row`. Example classes:

- tiny rows
- short rows
- medium rows
- long rows

The goal is not elegance. The goal is to stop tiny rows and huge rows from poisoning each other’s efficiency.

### 8.2 Scheduling Ideas

- warp-per-row for short rows
- multi-warp or CTA-per-row for long rows
- specialized long-row kernels when heavy tails matter

### 8.3 Long-Row Rule

Long-row handling should reduce imbalance and memory stalls, not maximize occupancy on paper.

## 9. Multi-GPU Strategy On This Host

Use the real topology:

- pair A = `{0,2}`
- pair B = `{1,3}`

### 9.1 Why Row Sharding Usually Wins

Row sharding fits:

- CSR storage
- row-local preprocessing
- pair-local reductions
- sparse × dense projection with row outputs

### 9.2 Communication Rule

- communicate summaries, not raw sparse tensors, across pairs
- reduce within each NVLink pair first
- exchange leaders or reduced summaries across `PHB` before tolerating `SYS`

### 9.3 What Not To Do

- shard in a way that forces high-traffic sparse tensor exchange across pairs
- assume adjacent ordinals are the fast pair
- all-reduce large sparse structures without checking whether summary exchange is enough

### 9.4 NCCL Rule

Use NCCL for the communication that remains. Benchmark before setting topology-related env vars permanently.

## 10. Pipeline Template

### Stage A: Sparse Ingest And Cleanup

- coalesce duplicates
- choose stable layout
- normalize index widths

### Stage B: Sparse Cell-Wise Preprocessing

- QC
- row sums
- row normalization
- filtering
- fused transforms where justified

### Stage C: Sparse Feature-Wise Phase

- build CSC if repeated feature-wise passes justify it
- compute feature statistics efficiently

### Stage D: Sparse Projection

- use SpMM or a fused equivalent

### Stage E: Dense Downstream Phase

- switch to cuBLAS / cuBLASLt / cuSOLVER / cuVS as the matrix becomes dense enough

## 11. Anti-Patterns

- optimizing first for peak occupancy
- optimizing first for Tensor Core use on raw sparse count matrices
- over-converting formats because each phase was implemented in isolation
- writing fancy kernels before profiling cuSPARSE / CUB baselines
- using atomics as the default for repeated high-contention feature-wise aggregation
- ignoring `nnz/row` skew
- moving sparse data across pairs when row-local reduction would avoid it

## 12. What To Benchmark First

On real data, benchmark:

- CSR vs CSC strategy for the feature-wise phases
- SpMM vs repeated SpMV
- row-binned custom kernels vs one generic sparse kernel
- fused row-normalization passes vs multi-kernel pipelines
- pair-local row sharding with summary exchange vs more global communication

## Official References

- CUDA release notes: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html
- cuSPARSE: https://docs.nvidia.com/cuda/cusparse/index.html
- CUB / CCCL: https://nvidia.github.io/cccl/cub/
- Volta tuning guide: https://docs.nvidia.com/cuda/volta-tuning-guide/index.html
