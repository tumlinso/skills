# Hopper Low-Level Optimization

Use this route for deep H100-class tuning.

## What Actually Changes From Ampere

According to NVIDIA’s Hopper tuning guide, Hopper introduces features that
should change decomposition choices:

- Tensor Memory Accelerator for bulk multidimensional movement
- thread block clusters
- distributed shared memory across clustered blocks
- FP8 Tensor Core routing through Transformer Engine paths
- DPX for dynamic-programming-like patterns

Source: https://docs.nvidia.com/cuda/hopper-tuning-guide/index.html

## Do First

1. Decide whether the kernel wants a TMA pipeline instead of ordinary async copy.
2. Decide whether clustered execution changes producer-consumer ownership.
3. Decide whether the math path belongs on FP8 Tensor Cores.

## TMA Doctrine

Use TMA when:

- the data movement is large, regular, and tensor-shaped
- copy engines can feed a compute stage better than hand-issued load ladders
- the kernel already wants explicit staging and shared-memory reuse

Avoid forcing TMA when:

- the kernel is dominated by irregular addressing
- the staging unit is too small or too branchy
- the kernel is better expressed through a library path

## Clusters And Distributed Shared Memory

Use clusters when:

- multiple blocks cooperate on a tile or queue
- shared state really benefits from inter-block locality
- the synchronization cost is still lower than a global-memory round trip

Do not cluster by default. The extra structure must pay for itself.

## Tensor Core Routing

- Route dense Hopper-friendly work to cuBLASLt, CUTLASS, or Transformer
  Engine-backed stacks first.
- For Tensor Core-eligible custom ops, stay library-first longer than on Volta
  and own the kernel only when fusion, layout control, or repeated library glue
  is the real limiter.
- Keep the owned custom-kernel path available whenever the library route blocks
  the fused decomposition the workload actually needs.
- Use FP8 only when the numerical budget, software stack, and deployment target
  all agree.
- If bytes moved still dominate, do not force Tensor Core thinking onto a
  memory-bound phase.

## Profiling Questions

Ask:

- did TMA actually shift the kernel away from staging overhead
- did clustering reduce global traffic enough to justify the extra structure
- did FP8 routing fire the intended Tensor Core path
- is the kernel now limited by memory, occupancy, or cluster synchronization

## Build Rule

During deep Hopper tuning, build `sm_90` only. Add `compute_90` PTX only when
the question is future compatibility.
