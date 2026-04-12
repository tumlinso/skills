# scRNA-seq

Read this first for requests about gene-by-cell count matrices, UMI counts, transcript count tables, pseudobulk generation, or RNA-only single-cell workflows.

## Raw Inputs

- cell barcodes and gene features
- count matrix, usually sparse
- per-cell metadata: sample, donor, batch, chemistry, lane if available
- optional ambient RNA estimates, mitochondrial genes, spike-ins, or cell-cycle annotations

## Matrix Semantics

- rows and columns vary by toolchain; never assume orientation from file extension alone
- features are genes or transcripts, not peaks or proteins
- counts may be raw UMI counts, estimated counts, logged counts, CPM, or normalized residuals; confirm before transforming

## Preprocessing Order

1. Confirm raw vs processed state.
2. Align gene identifiers and feature naming policy.
3. Perform cell- and feature-level QC.
4. Remove or flag low-quality cells and likely empty droplets or doublets if that is in scope.
5. Normalize and transform only after QC unless the workflow explicitly requires a different order.
6. Select highly variable features only after defining the intended downstream task.

Then read `task-preprocessing.md` or the matching task branch.

## Assay Pitfalls

- Do not combine Ensembl IDs and gene symbols without a deterministic mapping policy.
- Do not compare raw counts to normalized matrices as if they are on the same scale.
- Do not regress out biological covariates by default.
- Do not pseudobulk before confirming cell labels, donor grouping, and replicate structure.
- Do not treat zero inflation as proof of dropout without checking chemistry and preprocessing assumptions.

## Unification Notes

- compatibility checks: feature namespace, species, chemistry, genome build, cell-calling policy, normalization state
- gene union is safer for storage, but gene intersection is often safer for strict integration
- if datasets were normalized differently, preserve that state in metadata and prefer reprocessing from the nearest common raw stage
