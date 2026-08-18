# Blackwell Kernel Mechanics

Use this route when the first unresolved design choice is fusion,
specialization, family-specific build choice, or library boundary.

## Blackwell Bias

- keep the kernel narrow until you know whether the win is Blackwell-specific
- do not force family-specific features onto phases that are still memory-bound
- prefer library-backed Tensor Core paths before handwritten kernels
