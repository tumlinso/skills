# scATAC-seq

Read this first for peak-by-cell matrices, fragment files, accessibility counts, gene-activity derivation, or chromatin accessibility integration.

## Raw Inputs

- fragment files or peak-by-cell count matrices
- peak definitions with genome build and chromosome naming convention
- cell metadata: sample, donor, batch, chemistry, barcode policy
- optional gene annotations, motif annotations, or QC summaries

## Matrix Semantics

- features are genomic intervals or derived bins, not genes unless the matrix is explicitly gene activity
- peak sets from different studies are usually not directly compatible
- extreme sparsity is expected; preserve sparse representations when possible

## Preprocessing Order

1. Confirm whether the data are fragments, called peaks, bins, or gene-activity scores.
2. Confirm genome build and chromosome naming compatibility.
3. Perform assay-specific QC.
4. Reconcile peak definitions before any merge or integration.
5. Only derive gene activity after deciding whether the downstream task needs it.

Then read `task-preprocessing.md` or the matching task branch.

## Assay Pitfalls

- Do not merge peak matrices with different peak universes without an explicit reconciliation policy.
- Do not treat gene activity as interchangeable with RNA expression.
- Do not densify large peak matrices without a strong reason.
- Do not ignore blacklist regions, TSS enrichment, or fragment-depth differences when QC is in scope.

## Unification Notes

- compatibility checks: genome build, chromosome naming, peak caller or peak set policy, fragment-vs-peak provenance, binning strategy
- safest merge path is often to rebuild a unified peak set from compatible raw or near-raw inputs
- when raw fragments are unavailable, document that the merged peak space is an approximation
