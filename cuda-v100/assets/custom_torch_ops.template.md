# Custom Torch Ops

Use this file as the project-level registry for nontrivial custom Torch operations.

## How To Use This File

- Add one section per op.
- Create the entry when the op is first proposed.
- Update the same entry as implementation and validation progress.
- Mark replaced ops as `deprecated` instead of silently deleting them.

## Entry Template

### `<op_name>`

- Purpose:
- Owning model or component:
- Status: proposed
- Python API boundary:
- C++ binding boundary:
- CUDA or library backend:
- Input contract:
- Output contract:
- Dtype, layout, and device assumptions:
- Backward or autograd notes:
- Distributed implications:
- Code location:
- Validation notes:
