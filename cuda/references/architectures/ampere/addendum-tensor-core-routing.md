# Ampere Tensor Core Routing

Use this route when the task is TF32, BF16, FP16, or structured-sparsity
routing on A100.

Primary sources:

- https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html
- https://docs.nvidia.com/cuda/cusparselt/index.html

## Route Hard When

- dense blocked math maps cleanly to Tensor Core libraries
- TF32 is acceptable for FP32-heavy dense work
- BF16 or FP16 already fit the numerical budget

## Stay Off This Path When

- the phase is sparse, irregular, or memory-bound
- the 2:4 contract does not actually hold
- the bytes moved still dominate after reformulation
