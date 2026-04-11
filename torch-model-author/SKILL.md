---
name: torch-model-author
description: Choose and design new PyTorch or libtorch models for a task, especially bioinformatics and omics workloads that must run well on a 4-GPU Tesla V100 machine. Use when Codex needs to decide what model family fits the problem, such as time-evolution models, autoencoders, diffusion models, transformers, graph models, or multimodal hybrids; when the task requires full architecture, loss, and training-plan design; when distributed strategy on the 4x V100 host matters; or when the model may require custom Torch CUDA ops that should be tracked in a repo-local custom_torch_ops.md registry and implemented with cuda-v100.
---

# Torch Model Author

Use this skill to choose and design new models, not just to implement layers that were already decided elsewhere.

This skill is bioinformatics-first. Default to omics, single-cell, multimodal, perturbation, spatial, and longitudinal biology interpretations unless the user clearly wants a different domain.

Use the sibling `cuda-v100` skill for:

- hardware-aware memory fit
- 4x V100 topology and DDP tuning
- custom Torch CUDA extensions
- low-level CUDA and profiler-driven optimization

## Workflow

1. Classify the task before naming a model family.
   - discriminative prediction
   - latent representation or denoising
   - generative synthesis or imputation
   - time evolution or trajectory
   - graph or interaction reasoning
   - multimodal fusion

2. Choose the authoring surface.
   - Python PyTorch for experimentation, training loops, and faster iteration
   - libtorch when the user explicitly wants C++ frontend authoring, tighter C++ integration, or deployment constraints that justify it
   - dual surface by default: plan the model so the core tensor contracts and custom-op boundaries can survive a later libtorch implementation

3. Read `references/model-family-selection.md` first.
   - use it to choose between temporal models, autoencoders, diffusion, graph models, transformers, and hybrids

4. Read `references/bioinformatics-model-playbook.md` for bioinformatics and omics tasks.
   - use it for scRNA-seq, ATAC, multimodal, perturbation, spatial, and longitudinal model choices

5. Read `references/distributed-4gpu-planning.md` before proposing large models.
   - use it to decide whether the model should be single-GPU first or designed for 4-GPU DDP from the start

6. Bootstrap the project custom-op registry when custom ops are plausible.
   - detect repo root with `git rev-parse --show-toplevel 2>/dev/null || pwd`
   - if `<repo_root>/custom_torch_ops.md` does not exist, create it from `assets/custom_torch_ops.template.md`
   - record proposed ops before handing off to `cuda-v100`
   - read `references/custom-op-registry-convention.md` for the required schema

7. Hand off to `cuda-v100` when the answer depends on hardware details.
   - use `cuda-v100` for memory budgeting, DDP topology, host-device pipeline, or custom Torch CUDA extensions

## Reference Map

- `references/model-family-selection.md`: decision rules for choosing model families from the task shape
- `references/bioinformatics-model-playbook.md`: explicit model guidance for omics, multimodal, temporal, and perturbation workloads
- `references/distributed-4gpu-planning.md`: architecture constraints and distributed choices for the 4x V100 host
- `references/custom-op-registry-convention.md`: how to create and maintain repo-local `custom_torch_ops.md`

## Common Sequences

- `references/model-family-selection.md` -> `references/bioinformatics-model-playbook.md`: choose the family, then specialize it to the biology and assay
- `references/model-family-selection.md` -> `references/distributed-4gpu-planning.md`: choose the family, then reshape width, depth, sequence length, and batch plan for 4x V100
- `references/model-family-selection.md` -> `references/custom-op-registry-convention.md` -> `cuda-v100`: record required custom ops first, then design and implement them with hardware-aware constraints
- `references/bioinformatics-model-playbook.md` -> `cuda-v100`: start with the biology-driven architecture choice, then optimize fit and distributed execution

## Output Requirements

Be explicit about:

- the task framing and which objective dominates
- the recommended model family and why it beats the main alternatives
- whether the plan targets Python PyTorch, libtorch, or a dual path
- the input representation and any sparse-to-dense boundary
- the backbone, latent structure, decoder or heads, and loss design
- whether the model should be single-GPU first or 4-GPU by design
- which custom Torch ops, if any, should be registered in `custom_torch_ops.md`
- which questions must be handed off to `cuda-v100`

Hard constraints:

- Do not recommend diffusion by default when a lighter conditional generative model is enough.
- Do not recommend a communication-heavy multi-GPU design if the model cleanly fits and trains on one V100 first.
- Do not treat temporal biology as a static embedding problem unless the user only needs a static representation.
- Do not invent custom CUDA ops when library-backed kernels or existing PyTorch ops are adequate.
