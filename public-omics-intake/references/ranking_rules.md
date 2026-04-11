# Ranking Rules

Use the ranking module to estimate likely integratability rather than only textual relevance.

The default weights live in `scripts/default_ranking_weights.json`. They intentionally bias toward:

- species match
- modality match
- assay or chemistry compatibility
- processed matrix availability
- metadata richness
- stable linked identifiers

## Factor Intent

- `species_match`: prioritize the requested organism. Leave neutral when no organism filter was supplied.
- `stage_match`: reward overlap with developmental or disease timing when the user specified it.
- `modality_match`: reward direct modality overlap such as scRNA-seq, scATAC-seq, CITE-seq, multiome, or spatial.
- `assay_compatibility`: reward compatible assay or chemistry even when the modality label is incomplete.
- `processed_matrices`: reward studies that already expose processed matrices or matrix-like public files.
- `raw_files`: treat raw availability as a useful capability, not a default preference.
- `metadata_richness`: reward studies with populated title, summary, tissue, stage, perturbation, and linked identifiers.
- `linked_accessions`: reward clear study to sample to run relationships.
- `public_access`: penalize restricted or unclear access.
- `integration_ease`: composite signal from processed availability, metadata quality, linkage, modality, and identifier consistency.
- `identifier_consistency`: reward stable identifiers across study, sample, and run layers.

## Interpretation

- Higher score means better first-pass integration candidate.
- A higher score does not guarantee biological suitability.
- Low-score candidates may still be worth retaining when the biology is rare and coverage is sparse.
- When candidates are close, prefer the one with clearer processed files and better metadata.

## Default Tie Break

Sort by:

1. descending `integratability_score`
2. accession in stable lexical order
