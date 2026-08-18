# Ampere Programming Guide

Use this route for overall A100-class strategy.

Primary source:
https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html

## What Actually Changes From Volta

- async global-to-shared copy changes staging decisions
- split arrive-wait barriers change producer-consumer pipelines
- larger L2 changes some reuse decisions
- TF32 raises the default dense-math floor
- 2:4 structured sparsity can justify a separate library path

## Family Rules

1. Prefer `sm_80`-only builds while tuning.
2. Re-evaluate any Volta fusion plan that exists only to hide copy latency.
3. Push dense math onto cuBLASLt, CUTLASS, or cuDNN before hand-tuning.
4. Keep structured sparsity opt-in and measure-backed.
