---
name: v100-model-design
description: >-
  Entry skill for choosing and designing PyTorch or libtorch models that will
  run on a 4x Tesla V100 host. Use when Codex needs to pick a model family,
  objective, latent structure, decoder, multimodal fusion plan, temporal
  design, sparse-to-dense boundary, or custom-op boundary before handing off
  low-level implementation, fit, topology, or profiler work to `cuda-v100`.
  Keep the workflow routed: choose model family, distributed shape, or
  custom-op planning first, then escalate to `cuda-v100` only when hardware
  implementation becomes the main question.
---

# V100 Model Design

Use this as the public entry point for model design on the 4x V100 host.

Do not start in `cuda-v100` when the unresolved question is still architecture choice. Choose the model-design path first, then hand off only the remaining hardware-specific work.

## Choose Your Path

Choose the first statement that is true. Load only the file named in that row first.

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "What model family fits this task?", "should this be temporal, autoencoding, graph, diffusion, transformer, or hybrid?" | `references/route-model-family.md` | `references/bioinformatics-model-playbook.md` after the family is narrowed |
| "Will this design scale on 4 V100s?", "should this be single-GPU first or distributed from the start?" | `references/route-distributed-shaping.md` | `references/distributed-4gpu-planning.md` once the family is stable |
| "Do we need custom Torch ops?", "where should the custom-op boundary sit?" | `references/route-custom-op-planning.md` | `references/custom-op-registry-convention.md` before handing off to `cuda-v100` |
| "The real question is memory fit, DDP topology, staging, kernel shape, or profiler interpretation" | `cuda-v100` | return here only if model choice becomes unclear again |

## Opening Moves

### Path: Model Family

1. Classify the task objective before naming a model family.
2. Compare the leading family against the main alternatives.
3. Define the input representation, latent structure, decoder or heads, and loss.
4. Return here if scaling or custom-op questions become dominant.

### Path: Distributed Shaping

1. Assume single-GPU first unless the design truly requires 4 GPUs.
2. Reshape width, depth, sequence length, batch plan, and modality fusion for the actual host.
3. Decide whether distributed design is a first-order requirement or later optimization.
4. Return here if hardware implementation details replace design questions.

### Path: Custom-Op Planning

1. Define the op boundary before talking about kernels.
2. Prefer library-backed Torch, ATen, cuBLAS, cuSPARSE, or CUTLASS paths when they are adequate.
3. Record any real custom op in `custom_torch_ops.md` before implementation.
4. Hand off to `cuda-v100` only after the boundary is stable.

## Handoff Rule

Use `cuda-v100` for:

- memory budgeting
- DDP or NCCL topology
- host-device pipeline issues
- Torch CUDA extension implementation
- low-level CUDA or profiler-driven optimization

Do not bounce between this skill and `cuda-v100` repeatedly. Stay here until the model decision is stable.

## Reference Map

- `references/route-model-family.md`
- `references/route-distributed-shaping.md`
- `references/route-custom-op-planning.md`
- `references/model-family-selection.md`
- `references/bioinformatics-model-playbook.md`
- `references/distributed-4gpu-planning.md`
- `references/custom-op-registry-convention.md`

## Assets

- `assets/custom_torch_ops.template.md`: template for bootstrapping `<repo_root>/custom_torch_ops.md`

## Hard Boundaries

- Do not recommend diffusion by default when a lighter conditional model is enough.
- Do not design a communication-heavy 4-GPU plan if the model fits and trains well on one V100 first.
- Do not invent custom CUDA ops when existing Torch or library-backed paths are adequate.
- Do not use this skill for low-level Volta tuning once the unresolved question is implementation rather than model design.
