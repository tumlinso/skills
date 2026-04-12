# Route: Model Family

Use this route when the main uncertainty is what architecture should exist at all.

## Use When

- choosing between temporal, autoencoder, graph, transformer, diffusion, or hybrid families
- deciding whether the task is discriminative, generative, denoising, latent, or multimodal
- choosing Python PyTorch, libtorch, or a dual path

## First Move

Read `references/model-family-selection.md` first.

Then, for bioinformatics or omics tasks, load `references/bioinformatics-model-playbook.md`.

## Load Next Only If

- load `references/distributed-4gpu-planning.md` when model width, depth, batch plan, or sequence shape must be constrained by the 4x V100 host
- switch to `references/route-custom-op-planning.md` when the chosen family seems to need nontrivial custom ops
- hand off to `cuda-v100` only after the architecture is already stable

## Return To Root When

- the family, objective, and losses are stable and the next question is scale or implementation
