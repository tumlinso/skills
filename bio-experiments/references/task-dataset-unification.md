# Task: Dataset Unification

Read this when the request is to merge, align, standardize, or clean up more than one dataset before or instead of integration.

Always read `hard-constraints.md` with this file.

## Compatibility Checklist

- same species or an explicit cross-species mapping policy
- compatible genome build and chromosome naming for genomic assays
- compatible feature namespace or a deterministic mapping plan
- known preprocessing state for every dataset
- explicit donor, sample, batch, study, chemistry, and platform metadata where available
- explicit modality coverage and missingness policy

## Unification Order

1. Normalize metadata schema and controlled vocabularies.
2. Record provenance fields before modifying identifiers.
3. Reconcile feature identifiers.
4. Decide union vs intersection vs rebuilt common feature space.
5. Refuse silent merges when input states are incompatible.
6. Preserve per-dataset preprocessing state in metadata after the merge.

## Decision Rules

- prefer reprocessing from a common raw stage when datasets were transformed differently
- prefer explicit feature-space reconciliation over padding with unlabeled columns
- prefer keeping incompatible modalities separate rather than inventing missing values without policy
- if peak sets or antibody panels differ substantially, warn that simple concatenation is not scientific harmonization

## Common Failure Modes

- gene symbols duplicated after identifier conversion
- batch labels reused with different meanings across studies
- study-specific filtering causing hidden coverage differences
- processed embeddings treated as equivalent to assay matrices
