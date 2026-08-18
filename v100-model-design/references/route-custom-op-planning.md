# Route: Custom-Op Planning

Use this route before any Torch CUDA extension work.

## Use When

- the model may need a custom Torch op
- the unresolved question is where the extension boundary should sit
- you need to decide what belongs in Python, C++, or CUDA

Do not use this route when the real question is broader:

- Torch or libtorch should be bypassed for an entire hot subsystem
- the subsystem may own backward logic directly
- the subsystem may own optimizer or update logic directly
- the trainer boundary itself may need to move below the framework

Those cases belong in `references/route-low-level-ml-boundary.md`.

## First Move

Read `references/custom-op-registry-convention.md`.

Then:

1. detect the repo root
2. bootstrap `custom_torch_ops.md` from `assets/custom_torch_ops.template.md` if it does not exist
3. record the proposed op boundary and why built-in Torch or library-backed paths are insufficient

## Load Next Only If

- return to `references/route-model-family.md` if the need for custom ops suggests the architecture itself should change
- switch to `references/route-low-level-ml-boundary.md` if the component may own backward, optimizer, or trainer logic outside Torch or libtorch
- hand off to `cuda` once the op boundary is recorded and the remaining questions are implementation, fit, or profiling

## Return To Root When

- the op registry is updated and the next uncertainty is no longer model design
