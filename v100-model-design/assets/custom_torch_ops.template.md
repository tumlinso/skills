# Custom Torch Ops And Low-Level ML Boundaries

Use this file as the project-level registry for nontrivial custom Torch operations and low-level ML subsystem boundaries.

## How To Use This File

- Add one section per op.
- Create the entry when the op is first proposed.
- Update the same entry as implementation and validation progress.
- Mark replaced ops as `deprecated` instead of silently deleting them.

## Entry Template

### `<op_or_subsystem_name>`

- Purpose:
- Owning model or component:
- Status: proposed
- Framework bypass rationale:
- Framework boundary:
- Python API boundary:
- C++ binding boundary:
- CUDA, library, or framework-free backend:
- Input contract:
- Output contract:
- Dtype, layout, and device assumptions:
- Backward or autograd notes:
- Optimizer or update ownership:
- Trainer-loop ownership:
- Distributed implications:
- Code location:
- Validation notes:
