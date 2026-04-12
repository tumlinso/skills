# Spatial Transcriptomics

Read this first for spot-level or cell-level spatial transcriptomics, coordinate-aware expression data, histology-linked assays, or neighborhood graph construction.

## Raw Inputs

- expression matrix
- spatial coordinates
- slide, image, or field-of-view identifiers
- metadata: sample, section, donor, batch, platform
- optional segmentation masks, images, or spot geometry

## Matrix Semantics

- observations may be spots, segmented cells, beads, or pixels depending on platform
- coordinates are part of the data model, not decoration
- spot-level measurements can mix multiple cells; do not assume single-cell semantics without confirmation

## Preprocessing Order

1. Confirm the observation unit.
2. Confirm coordinate system and image linkage.
3. Run assay-appropriate QC on expression and spatial coverage.
4. Preserve slide and section provenance before any merge.
5. Decide whether downstream code is expression-only or spatially aware.

Then read `task-preprocessing.md` or the matching task branch.

## Assay Pitfalls

- Do not treat spot data as single-cell data without qualification.
- Do not drop spatial coordinates during merges if downstream analysis may use them.
- Do not merge across slides without tracking section and imaging provenance.
- Do not assume comparable spot resolution across platforms.

## Unification Notes

- compatibility checks: platform, coordinate system, observation unit, image linkage, section provenance, normalization state
- if harmonizing across platforms, preserve platform metadata and warn that spatial resolution differences can dominate the correction target
