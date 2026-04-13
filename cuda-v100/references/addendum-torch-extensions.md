# Addendum: Torch Extensions

Use this addendum when the task is to write, debug, or optimize a PyTorch C++ or CUDA extension that must run well on Tesla V100.

If the extension still segfaults or hits a CUDA hard failure before normal tuning can begin, route first into `references/addendum-crash-debugging.md`. Return here after the crash class is stable enough to work on the extension boundary.

Use it when questions look like:

- how should this custom op be structured between Python, C++, and CUDA?
- when should the extension call cuBLAS, cuSPARSE, or a custom kernel?
- how should the op use the current PyTorch CUDA stream correctly?
- what compile flags and dispatch rules should be used for Volta `sm_70`?
- what tensor layout, dtype, and contiguity checks should happen at the C++ boundary?
- how should repo-local custom ops be tracked for the model or project?

## Workflow

1. Bootstrap the project registry first.
   - detect repo root with `git rev-parse --show-toplevel 2>/dev/null || pwd`
   - if `<repo_root>/custom_torch_ops.md` does not exist, create it from `assets/custom_torch_ops.template.md`
   - add or update an entry before implementing a nontrivial custom op

2. Define the op boundary.
   - inputs, outputs, shapes, dtypes, and mutation rules
   - forward only or forward plus backward
   - single fused op or several smaller ops

3. Keep the Python layer thin.
   - argument normalization, optional autograd wrapper, and registration
   - do not hide expensive shape transforms or copies in Python glue

4. Keep the C++ binding explicit.
   - validate device, dtype, contiguity, and layout assumptions
   - use ATen tensors for integration and raw CUDA or library calls for the real backend
   - use the current CUDA stream and guard the correct device

5. Choose the backend deliberately.
   - cuBLAS or cuBLASLt for dense math
   - cuSPARSE or CUB for sparse primitives
   - custom CUDA only when the op is glue-heavy, irregular, or fusion removes real traffic

6. Target Volta directly.
   - build for `sm_70`
   - do not assume TF32, BF16 Tensor Core fast paths, or `cp.async`
   - tune launch geometry, register pressure, and memory traffic against V100 limits

7. Add backward only when necessary.
   - prefer composing backward from stable library primitives when that preserves throughput
   - write custom backward kernels only when the decomposition cost is material

8. Resume the main `cuda-v100` workflow once the extension boundary is correct and the remaining work is standard Volta CUDA tuning.

## Support References

- Read `references/torch-extension-playbook.md` for extension layout, registration patterns, stream handling, error checks, build flags, and packaging rules.
- Read `references/custom-torch-ops-registry.md` for the repo-root registry convention and the required `custom_torch_ops.md` schema.
- Read `references/addendum-crash-debugging.md` first when the extension cannot run stably enough for ordinary profiling or tuning.
- Read `references/v100_cuda_cpp_optimize.md` for lower-level Volta kernel and libtorch or ATen integration rules after the extension boundary is set.
- Read `references/addendum-kernel-roofline-lab.md` if the extension already works and the remaining problem is hot-kernel efficiency.

## Output Requirements

Be explicit about:

- where the extension boundary should sit
- which parts belong in Python, C++, and CUDA
- whether the backend should be library-backed or custom-kernel
- whether `custom_torch_ops.md` was created or updated and what entry changed
- which tensor assumptions must be checked at the binding boundary
- which V100-specific compile or tuning rules matter for this op
