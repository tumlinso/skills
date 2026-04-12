# Task: Integration

Read this when the request asks for batch correction, harmonization, shared latent spaces, anchors, multimodal alignment, or integrated embeddings.

Always read `hard-constraints.md` with this file.

Bias toward aggressive harmonization only after compatibility checks pass and the biological objective is stated clearly.

## Preconditions

- assay-specific QC is complete
- feature-space reconciliation is complete
- processing state is known for every dataset and modality
- donor, batch, study, chemistry, and platform metadata are available or explicitly absent

## Method Selection

- direct concatenation: only for already compatible datasets with minimal batch structure
- anchor or neighbor-based alignment: use for same-modality datasets that share a meaningful biological manifold
- latent integration: use when the downstream objective values a common representation over exact raw-space comparability
- multimodal graph or cross-modal alignment: use when modalities are distinct but linked at the cell or donor level

## Aggressive Harmonization Rules

- remove technical structure, not the experimental question
- inspect whether donor, condition, or rare-cell signal may be the same axis as batch
- preserve raw or minimally processed objects alongside integrated representations
- require a warning when rare states, temporal gradients, perturbation effects, or spatial structure may be compressed

## Red Flags

- integrating different peak sets without reconstruction
- integrating RNA and gene-activity as if they were the same measurement
- using integrated embeddings as a replacement for raw matrices in every downstream step
- applying the same correction recipe across modalities without modality-specific justification
