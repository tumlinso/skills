# Ampere Low-Level Optimization

Use this route for deep A100-class tuning.

## What Actually Changes From Volta

NVIDIA documents several Ampere features that should change implementation
choices, not just tuning constants:

- async global-to-shared copy reduces register staging pressure and can overlap
  with compute
- split arrive-wait barriers support finer-grained producer-consumer pipelines
- larger L2 and residency controls can change reuse strategy
- TF32 Tensor Core routing raises the floor for dense math that stayed on CUDA
  cores on Volta
- structured sparsity is worth pursuing only when the problem actually matches
  the 2:4 contract

Source: https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html

## Do First

1. Decide whether the kernel is staging-limited or Tensor-Core-eligibility
   limited.
2. Replace register-heavy manual copy ladders with `cp.async` pipelines only
   when the access pattern is regular enough to benefit.
3. Keep narrow architecture-specific builds while tuning.

## Async Copy Doctrine

Use `cp.async` when:

- the tile load is regular
- the copy-compute overlap window is large enough to hide latency
- register pressure from ordinary loads is already hurting occupancy

Avoid forcing it when:

- the data is sparse or irregular enough that control flow dominates
- the tile is too small to repay the pipeline complexity
- the kernel is already limited elsewhere

## Tensor Core Routing

- Push dense GEMM-like work toward cuBLASLt, CUTLASS, or cuDNN first.
- For Tensor Core-eligible custom ops, prefer library-backed Tensor Core paths
  first and own the kernel only when fusion, blocked layout control, or
  measurable library glue overhead justifies it.
- Keep the owned custom-kernel option available whenever the right fused path
  cannot live cleanly at the library boundary.
- Use TF32 aggressively for FP32-heavy dense training or inference when the
  numerical budget allows it.
- Use BF16 or FP16 when the workload already tolerates reduced precision and
  bytes moved or Tensor Core throughput dominate.
- Structured sparsity is a special path, not a default path. Pursue it only
  when weights or blocks naturally satisfy the 2:4 contract or can be trained
  into it without breaking the model.

## L2 And Residency

Ampere A100’s larger L2 means you should revisit reuse assumptions copied from
Volta. Reuse that was not worth staging on V100 may now fit in a cache-first
plan, but only measure-backed data should decide that.

## Profiling Questions

Ask:

- did async staging reduce register pressure or just add complexity
- is the kernel still memory-pass bound after staging changes
- did TF32 or BF16 route the kernel onto Tensor Cores
- are L2 hit-rate and residency behavior strong enough to justify the current
  tile and reuse plan

## Build Rule

During deep Ampere tuning, build `sm_80` only. Add `compute_80` PTX only when
the question is portability rather than pure local performance.
