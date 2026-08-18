# Blackwell Tensor Core Routing

Use this route when the task is FP4, microscaling, or Blackwell Tensor Core
routing.

Primary sources:

- https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html
- https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/

## Route Hard When

- dense blocked math maps cleanly to Blackwell-aware libraries
- the numerical budget explicitly allows FP4 or related low-precision routes

## Stay Off This Path When

- the phase is sparse, irregular, or memory-bound
- the optimization is really a system-topology question
