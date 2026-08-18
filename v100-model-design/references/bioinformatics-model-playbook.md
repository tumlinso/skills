# Bioinformatics Model Playbook

Use this reference when the task is biological, omics-heavy, or single-cell.

## scRNA-seq Representation And Denoising

Default families:

- denoising autoencoder
- VAE or conditional VAE

Use these when the goal is:

- latent embedding
- denoising
- batch correction
- donor or condition-aware integration

Avoid diffusion unless the user explicitly needs generative synthesis or richer conditional sampling.

## scRNA-seq Time Evolution And Perturbation

Default families:

- temporal latent variable model
- latent ODE or neural ODE
- recurrent or state-space latent dynamics model

Use these when the goal is:

- trajectory prediction
- perturbation response across time
- state transition modeling
- velocity-adjacent evolution questions

Static autoencoders can still provide the encoder, but they are not sufficient by themselves when the target is evolution.

## ATAC And Accessibility

Default families:

- sparse encoder plus autoencoder or topic-style latent model
- graph-enhanced encoder when regulatory structure is real

Key rule:

- keep sparse preprocessing and feature filtering explicit outside the network when possible
- do not densify early just to force a fashionable architecture

## Multimodal Single-Cell

Default families:

- shared-latent VAE
- contrastive plus reconstruction hybrid
- modality-specific encoders with shared latent fusion

Use graph refinement only when cell-cell or feature-feature structure is part of the real task.

## Spatial And Interaction Tasks

Default families:

- graph neural network
- spatial message-passing model
- hybrid encoder plus graph refinement

Use these when adjacency or neighborhood structure carries genuine signal.

## Generative Biology

Default families:

- conditional VAE for lighter-weight conditional generation
- latent diffusion when fidelity and sample diversity matter enough to justify the extra cost

On 4x V100:

- prefer latent-space generation over raw high-dimensional generation
- check memory and communication costs before committing to diffusion

## Custom Ops In Bioinformatics Models

Custom ops are most likely to be justified for:

- irregular sparse aggregation
- fused normalization or masking over omics-specific layouts
- repeated sparse compaction or remapping

Route sparse or nonstandard-layout training questions into `references/sparse-layout-training-boundary.md` first when the real issue is:

- framework overhead from sparse metadata churn
- backward state that should stay in a custom layout
- optimizer state that should stay sparse or blocked
- a low-level trainer boundary around a hot omics subsystem

Use the ordinary custom-op route only when the unresolved question is still a normal extension boundary. Hand implementation to `cuda` only after the boundary, gradient ownership, and optimizer ownership are stable.
