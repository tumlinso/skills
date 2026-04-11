# Addendum: Bio Data Layouts

Use this addendum when V100 optimization depends on understanding biological matrix meaning, sparse bio data phases, or layout semantics.

Use it to answer questions like:

- what does this matrix represent physically or biologically?
- is this phase row-wise or feature-wise?
- should this stay sparse or go dense?
- is CSR still the right master layout?
- where will memory traffic and imbalance come from?

## Workflow

1. Identify the matrix meaning.
   - cells x genes, cells x peaks, spliced or unspliced, graph edges, or dense embeddings
   - counts, normalized values, binary accessibility, or dense projected features

2. Identify the hot phase.
   - row-wise QC or normalization
   - feature-wise statistics
   - sparse x dense projection
   - filtering, compaction, or remapping
   - neighborhood or downstream dense work

3. Choose the master layout for the hot phase.
   - CSR when work is cell-wise
   - CSC when work is repeatedly feature-wise
   - COO only for assembly or transient construction
   - BSR or SELL only when structure is real and stable enough to justify it

4. Decide where sparse ends.
   - stay sparse while the matrix is huge, irregular, and mostly zeros
   - go dense only after feature selection, aggregation, or projection makes dense math dominant

5. Resume the main `cuda-v100` workflow once the data and phase boundaries are clear.

## Support References

- Read `references/bio-data-phases.md` to map common biological matrices and stages to row-wise, feature-wise, sparse, and dense phases.
- Read `references/bio-format-decision-tables.md` to decide CSR vs CSC vs COO vs structured formats and to spot when a transpose or projected dense stage is justified.
- Read `references/v100_bioinformatics_guide.md` when the resulting path still needs Volta-specific sparse kernel and pipeline guidance.

## Script

- Use `scripts/inspect_sparse_matrix.py` to inspect sparsity, row skew, and simple layout recommendations from exported matrix summaries.

## Output Requirements

Be explicit about:

- what the matrix axes mean
- which phase is hot
- which layout should be primary
- whether the workload should stay sparse or become dense
- what information should be carried into the main `cuda-v100` workflow for low-level optimization
