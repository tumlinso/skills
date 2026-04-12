# Task: Preprocessing

Read this when the request is to build, repair, or explain a preprocessing pipeline for a selected assay.

## Pipeline Skeleton

1. Confirm assay and raw input type.
2. Confirm whether the matrix is raw, filtered, normalized, transformed, imputed, or batch-corrected.
3. Run assay-specific QC before irreversible transformations.
4. Standardize feature identifiers and metadata schema early.
5. Apply normalization and transformation appropriate for the assay and modality.
6. Persist processing-state metadata so later code can avoid double-processing.

## Required Checks

- matrix orientation is explicit
- feature identifiers have a stable namespace
- observation metadata include donor, sample, batch, and study when available
- QC thresholds are parameterized, not silently hard-coded to one dataset
- sparse matrices stay sparse unless a downstream algorithm requires densification

## Assay-Specific Notes

- scRNA-seq: filter and QC before log normalization; confirm mitochondrial and ribosomal feature definitions
- scATAC-seq: resolve genome build and peak definitions before merging matrices
- CITE-seq: preprocess RNA and ADT separately before fusion
- spatial: preserve coordinates and section provenance
- multimodal: preprocess each modality independently before joint operations

## When To Escalate To Another Branch

- if more than one dataset must be aligned, also read `task-dataset-unification.md`
- if the request asks for batch correction or latent alignment, switch to `task-integration.md`
- if the output must feed a model directly, also read `task-model-inputs.md`
