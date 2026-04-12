# CITE-seq

Read this first for paired RNA and antibody-derived tag data, joint RNA plus protein matrices, or workflows that align transcript and surface-protein measurements.

## Raw Inputs

- RNA count matrix
- ADT count matrix
- shared or alignable cell barcode space
- metadata: sample, donor, batch, chemistry, antibody panel

## Matrix Semantics

- RNA features and ADT features are different modalities with different count distributions
- ADT panels may differ across studies even when RNA features overlap
- cell alignment must be confirmed, not assumed from filename proximity

## Preprocessing Order

1. Confirm paired-cell barcode mapping across modalities.
2. QC RNA and ADT with modality-appropriate metrics.
3. Normalize RNA and ADT with modality-aware methods.
4. Harmonize antibody panel identifiers before cross-study merges.
5. Decide whether downstream code needs early fusion, late fusion, or separate modality branches.

Then read `task-preprocessing.md` or the matching task branch.

## Assay Pitfalls

- Do not apply RNA normalization assumptions to ADT counts.
- Do not collapse unmatched antibody panels without documenting what was dropped or mapped.
- Do not silently discard cells missing one modality unless the task explicitly requires complete cases.
- Do not mix ambient correction or denoising assumptions across modalities.

## Unification Notes

- compatibility checks: shared barcode policy, ADT panel overlap, antibody naming normalization, species, chemistry, processing state per modality
- keep modality-specific preprocessing metadata separate even when later building a joint object
