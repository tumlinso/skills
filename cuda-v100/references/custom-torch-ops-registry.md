# Custom Torch Ops Registry

Use this reference when `cuda-v100` needs to create or update a repo-local `custom_torch_ops.md`.

## Purpose

Keep a single project-level registry of custom Torch ops so model planning, CUDA implementation, and validation all point at the same contracts.

Use the registry when:

- a model depends on a nontrivial custom Torch op
- an op is being proposed but not yet implemented
- the op boundary or backend choice is changing
- validation status must be tracked across Python, C++, and CUDA layers

## Location Rule

Find the project root with:

```bash
git rev-parse --show-toplevel 2>/dev/null || pwd
```

Treat that directory as `<repo_root>`. The registry path is:

```text
<repo_root>/custom_torch_ops.md
```

If the file does not exist, create it from `assets/custom_torch_ops.template.md`.

## Required Entry Schema

Each op entry must capture:

- op name
- purpose
- owning model or pipeline component
- status: proposed, implemented, validated, or deprecated
- Python API boundary
- C++ binding boundary
- CUDA or library backend choice
- input and output contract
- dtype, layout, and device assumptions
- backward or autograd notes
- distributed implications
- code location

## Update Rules

- Add the entry when the op becomes part of the plan, not after code already exists.
- Update the status when the op moves from proposed to implemented or validated.
- Record when the op was replaced by a library path and mark it deprecated instead of silently deleting the history.
- Keep the registry at the project level, not per submodule, unless the repository already has a stronger convention.
