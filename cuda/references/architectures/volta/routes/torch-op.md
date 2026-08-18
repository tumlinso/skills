# Volta Torch-Op Route

Use for PyTorch C++ or CUDA extensions on native V100.

Rules:

1. Keep Python thin; keep the real boundary in C++ and CUDA.
2. For dense or blocked math, check Tensor Core ownership before accepting a regular custom kernel.
3. If the extension is mostly a thin wrapper around repeated library launches, reconsider the op boundary or own the fused kernel.
4. If the op is still crashing, stop and switch to crash triage first.

Load order:

1. `references/addendum-torch-extensions.md`
2. `references/torch-extension-playbook.md` only for binding, stream, build, and registry specifics
3. `references/architectures/volta/routes/tensor.md` when the op owns Tensor Core-eligible math
4. `references/architectures/volta/routes/fusion.md` when the real loss is HBM-pass-heavy glue
