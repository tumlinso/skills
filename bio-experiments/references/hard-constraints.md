# Hard Constraints

Load this file whenever code will merge datasets, integrate batches, construct model inputs, or transform data with unclear processing state.

## Never Do These Blindly

- merge datasets without checking feature-space compatibility
- normalize, log-transform, scale, impute, or batch-correct data twice
- treat gene symbols, Ensembl IDs, peaks, proteins, spots, and cells as interchangeable entities
- discard donor, batch, study, chemistry, platform, or modality provenance during preprocessing
- densify large sparse assays without a concrete downstream need and memory check
- treat integrated embeddings as a drop-in replacement for raw assay matrices
- perform train and validation splits after leakage has already been introduced by preprocessing or grouping

## Must-State Assumptions

- assay and modality
- raw input type
- processing state already completed
- feature identifier namespace
- observation unit: cell, nucleus, spot, fragment aggregate, or donor-level profile
- compatibility policy: union, intersection, remap, rebuild, or refuse merge

## Must-Check Provenance

- species
- genome build where relevant
- donor and sample identity
- study and batch labels
- chemistry and platform
- modality coverage and missingness

## Escalate Risks In The Answer

- over-correction could erase condition, lineage, temporal, perturbation, or spatial signal
- feature-space reconciliation may change biological meaning
- gene-activity or latent embeddings are approximations, not direct measurements
- processed inputs may be unsuitable for methods expecting raw counts
