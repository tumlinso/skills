# Task: Model Inputs

Read this when the request is to export tensors, build sparse matrices for training, generate train and validation splits, or prepare assay data for machine learning code.

Always read `hard-constraints.md` with this file when the inputs come from more than one dataset or from previously processed objects.

## Input Construction Rules

- record matrix orientation explicitly before writing tensor code
- preserve sparse formats for sparse assays unless the model requires dense input
- align feature ordering deterministically and persist the order
- keep per-modality tensors separate unless the model design requires early fusion
- represent missing modalities explicitly rather than dropping them silently

## Split Hygiene

- split on donor, study, sample, timepoint, or perturbation unit when leakage is possible
- do not let near-duplicate cells from the same source land in both train and validation unintentionally
- preserve provenance columns needed to rebuild or audit splits

## Processing-State Checks

- confirm whether inputs are raw, normalized, transformed, integrated, imputed, or denoised
- avoid feeding integration artifacts into objectives that require raw count semantics
- avoid mixing raw and processed modalities in a single model input without labeling the distinction

## Common Mistakes

- feature order mismatch between tensor export and metadata
- hidden densification of large sparse matrices
- training on batch-corrected embeddings while evaluating against raw-space labels without documenting the tradeoff
- cell-level splits that leak donor or study information
