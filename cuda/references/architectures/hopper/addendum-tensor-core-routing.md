# Hopper Tensor Core Routing

Use this route when the task is FP8 or Hopper Tensor Core routing.

Primary source:
https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html

## Route Hard When

- dense blocked math maps cleanly to Hopper-aware libraries
- FP8 is numerically acceptable and fully supported by the software stack

## Stay Off This Path When

- the phase is sparse, irregular, or memory-bound
- cluster or TMA structure matters more than raw math throughput
