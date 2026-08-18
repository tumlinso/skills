# Hopper Programming Guide

Use this route for overall H100-class strategy.

Primary source:
https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html

## What Actually Changes From Ampere

- Tensor Memory Accelerator changes the staging surface
- thread block clusters and distributed shared memory change producer-consumer
  ownership
- FP8 opens new Tensor Core routes
- DPX can matter for dynamic-programming-like patterns

## Family Rules

1. Prefer `sm_90`-only builds while tuning.
2. Revisit any Ampere pipeline that exists only to work around copy overhead.
3. Cluster only when the inter-block locality really pays for itself.
