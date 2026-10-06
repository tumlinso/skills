# Sparse Biological Workloads

Use this guide to classify a biological sparse matrix before choosing a kernel: record its axes (cells × genes, cells × peaks, spliced/unspliced counts, graph edges, or dense embeddings), value semantics (counts, normalized values, binary accessibility, projected features), and the hot phase.

## Match layout to the phase

- Cell-wise QC, row sums, normalization, filtering, row sharding, and sparse × dense projection usually favor CSR with rows = cells.
- Repeated gene/feature sums, means, variances, thresholds, or regression-like passes may justify CSC or a transposed representation. Compare repeated column work against the one-time conversion and reuse it across phases.
- Use COO for assembly or transient construction. Choose BSR, SELL, or blocked ELLPACK only when real stable block/row structure justifies padding and metadata costs.
- Stay sparse while the matrix is huge and mostly zero; cross to dense after feature selection, aggregation, or projection makes dense compute dominant.

Start from cuSPARSE and CUB/CCCL for standard sparse primitives, then use cuBLAS/cuBLASLt, cuSOLVER, or cuVS for reduced dense stages. Custom kernels earn their place when measured cost is glue: row skew, fused normalization/filtering, compaction/remap, irregular gathers/scatters, or launch-heavy preprocessing. Profile the full path around a fast primitive.

Use `scripts/inspect_sparse_matrix.py` on exported summaries to inspect sparsity and row skew. Its p99/mean flag is a screening summary: rare extreme rows beyond p99 can still dominate. Before dismissing skew, inspect the maximum, counts above useful row-length thresholds, or a row-length histogram. If source code still has CPU-shaped data structures or serial sparse loops, begin with [CPU-to-CUDA porting](cpu-porting.md) and [sparse rewrite choices](cpu-porting-sparse-bio.md). For biological stage meaning and format tradeoffs, read [data phases](bio-data-phases.md) or [format decisions](bio-format-decision-tables.md) as relevant. Load the [Volta sparse manual](sparse-bio-v100.md) only for V100-specific implementation, packing, and kernel strategy; its host topology is a recorded profile that must be checked at runtime.

When reporting a recommendation, name matrix axes, hot phase, chosen master format, sparse-to-dense boundary, and the conversion/packing costs to include in end-to-end measurement.
