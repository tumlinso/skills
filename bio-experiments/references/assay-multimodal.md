# Matched Multimodal Single-Cell

Read this first for paired or partially paired assays such as RNA plus ATAC, RNA plus protein, or multi-assay containers that share cell identities across modalities.

## Raw Inputs

- one matrix or file set per modality
- cell- or barcode-linkage information
- metadata: sample, donor, batch, chemistry, modality coverage
- optional modality-specific embeddings, peak sets, or feature annotations

## Matrix Semantics

- modalities may have different feature spaces, scales, sparsity patterns, and missingness
- pairing can be exact, partial, donor-level, or absent; confirm before designing joins
- some containers store assays with shared cells but different feature namespaces and preprocessing states

## Preprocessing Order

1. Confirm the pairing structure.
2. Perform modality-specific QC before fusion.
3. Record preprocessing state independently per modality.
4. Decide whether downstream code requires matched cells, cross-modal mapping, or modality-specific branches.
5. Reconcile missing-modality policy before filtering.

Then read `task-preprocessing.md` or the matching task branch.

## Assay Pitfalls

- Do not force a shared feature space across incompatible modalities.
- Do not drop partially observed cells without confirming the downstream objective.
- Do not treat donor-level alignment as cell-level pairing.
- Do not assume shared latent integration is equivalent to raw-data merging.

## Unification Notes

- compatibility checks: pairing granularity, modality coverage, preprocessing state per modality, feature namespaces, donor and batch metadata
- keep per-modality provenance intact even when building a joint container
