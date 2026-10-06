# Blackwell Programming Guide

Use for overall B100/B200-class strategy or when measured behavior points to
Blackwell-only features. Establish the exact device, software stack, and build
target; family-specific targets matter only when the code depends on those
features.

Primary sources: [Blackwell Tuning Guide](https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html)
and [Blackwell with CUDA 12.9](https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/).

## Family changes and baseline

- FP4 and microscaling broaden low-precision routing; accept them only when the
  numerical budget and software stack support the path.
- Deployment questions can depend on GB200 system topology. Separate a single
  GPU kernel question from system and collective behavior.
- Prefer a narrow Blackwell build while tuning. Use family-specific targets only
  when the code truly needs those features, and keep explicit fallback paths
  outside the family.

## Choose a direction from evidence

### Pipeline starvation

Prove starvation with Nsight Systems. Fix loader and staging problems before
touching low-precision kernel details. Revisit deployment assumptions if the
local pipeline is already healthy.

### Kernel structure and feature choice

Keep the kernel narrow until evidence shows a Blackwell-specific win. Do not
force family-specific features onto phases that remain memory-bound. Prefer
library-backed Tensor Core paths before handwritten kernels.

### Hot kernel

First confirm that the benchmark is representative. Check whether the limiter
is low-precision routing, memory traffic, or family-specific feature usage, then
change only the matching lever.

### Profiler interpretation

When reading Nsight output, ask whether the Blackwell-specific target changed
the hot path, whether FP4 or other low-precision routing reached the intended
Tensor Core path, and whether the limiter belongs to one kernel or the GB200
deployment shape.

### Memory fit and topology

Separate local memory-fit trouble from GB200 communication trouble. If the
deployment target is GB200 NVL72, use the
[GB200 NVL72 system guide](../../systems/gb200-nvl72.md) early. Keep collective
and topology experiments representative of deployment message sizes.

### Tensor Core routing

Route dense blocked math to Blackwell-aware libraries when it maps cleanly. Use
FP4 or microscaling only when the numerical budget explicitly allows the
precision. Avoid this route for sparse, irregular, or memory-bound phases, or
when the real issue is system topology.

### PTX

Read PTX only when explicitly requested and after isolating the hot path. First
decide whether family-specific target choice, Tensor Core routing, or GB200
deployment shape is still the real problem; dump only the focused symbol under
the target being studied.
