# Blackwell Low-Level Optimization

Use this route for deep B100 or B200-class tuning.

## Build Target Discipline

NVIDIA’s CUDA 12.9 guidance matters here:

- build binary code for each architecture you know the code will run on
- embed PTX for the newest architecture for future compatibility
- if you use family-specific features, use the family-specific targets with the
  `f` suffix and keep fallback code paths for other architectures

Source:
https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/

## What Actually Changes

According to NVIDIA’s Blackwell tuning guide and product material, Blackwell
pushes harder on:

- newest-generation Tensor Core paths
- FP4 and microscaling-driven low-precision routes
- family-specific architecture features exposed through newer CUDA targets
- deployment-scale coupling with Grace and GB200 rack topology

Sources:

- https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html
- https://docs.nvidia.com/multi-node-nvlink-systems/index.html

## Do First

1. Decide whether the workload should be library-backed before writing custom
   code.
2. Decide whether the optimization actually requires Blackwell family-specific
   features or only ordinary `sm_100` code generation.
3. Separate single-kernel tuning from GB200 deployment topology questions.

## Tensor Core And Precision Routing

- Push dense blocked math to cuBLASLt, CUTLASS, or other Blackwell-aware library
  paths first.
- For Tensor Core-eligible custom ops, keep the default library-first stance
  and move to owned kernels only when fusion, layout control, or measured glue
  overhead makes the library boundary the real bottleneck.
- Keep the owned custom-kernel option available whenever the needed fused path
  cannot be expressed cleanly inside the library boundary.
- Use FP4 or similar aggressive low-precision routes only when the numerical
  budget and software path are clearly compatible.
- Do not force FP4 onto memory-bound, sparse, or irregular phases just because
  the hardware supports it.

## Family-Specific Features

Use family-specific Blackwell targets only when:

- the code or library explicitly depends on those features
- the deployment target is known to stay inside the family
- you are willing to maintain fallback code outside the family

If not, prefer the ordinary architecture target and keep the code path portable.

## Profiling Questions

Ask:

- did the Blackwell-specific or family-specific target change the actual hot
  path
- is the kernel still limited by memory or launch structure instead of raw math
- should the optimization live in the library boundary instead of a handwritten
  kernel
- is the deployment question really about GB200 communication rather than one
  kernel

## Build Rule

During deep Blackwell tuning, build only the Blackwell architecture under study.
For family-specific features, emit the family-specific target plus a clear
fallback path rather than inflating one binary with unrelated architectures.
