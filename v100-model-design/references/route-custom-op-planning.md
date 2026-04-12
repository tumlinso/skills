# Route: Custom-Op Planning

Use this route before any Torch CUDA extension work.

## Use When

- the model may need a custom Torch op
- the unresolved question is where the extension boundary should sit
- you need to decide what belongs in Python, C++, or CUDA

## First Move

Read `references/custom-op-registry-convention.md`.

Then:

1. detect the repo root
2. bootstrap `custom_torch_ops.md` from `assets/custom_torch_ops.template.md` if it does not exist
3. record the proposed op boundary and why built-in Torch or library-backed paths are insufficient

## Load Next Only If

- return to `references/route-model-family.md` if the need for custom ops suggests the architecture itself should change
- hand off to `cuda-v100` once the op boundary is recorded and the remaining questions are implementation, fit, or profiling

## Return To Root When

- the op registry is updated and the next uncertainty is no longer model design
