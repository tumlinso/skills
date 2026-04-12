# Custom Op Registry Convention

Use this reference when model design suggests a nontrivial custom Torch op.

## File Rule

Create or update a repo-root file:

```text
custom_torch_ops.md
```

Find the repo root with:

```bash
git rev-parse --show-toplevel 2>/dev/null || pwd
```

If the file does not exist, create it from `assets/custom_torch_ops.template.md`.

## When To Add An Entry

Add an entry when:

- the model plan depends on a custom op
- the op is still only proposed
- a backend decision between library and custom CUDA must be preserved

Do not add an entry for trivial compositions of existing PyTorch ops that are unlikely to become stable project artifacts.

## Required Fields

Every entry should capture:

- op name
- purpose
- owning model or component
- status
- Python boundary
- C++ binding boundary
- CUDA or library backend
- contract and assumptions
- backward notes
- distributed implications
- planned or actual code location

## Handoff Rule

Once the entry exists, use `cuda-v100` for:

- Torch extension boundary design
- ATen and stream rules
- backend selection
- V100-specific kernel or memory decisions
