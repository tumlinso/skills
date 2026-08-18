# Blackwell Programming Guide

Use this route for overall B100 or B200-class strategy.

Primary sources:

- https://docs.nvidia.com/cuda/blackwell-tuning-guide/index.html
- https://developer.nvidia.com/blog/nvidia-blackwell-and-nvidia-cuda-12-9-introduce-family-specific-architecture-features/

## What Actually Changes From Hopper

- family-specific build targets matter when you depend on Blackwell-only
  features
- FP4 and microscaling push harder on low-precision routing
- deployment questions often couple directly to GB200 system topology

## Family Rules

1. Prefer a narrow Blackwell build while tuning.
2. Use family-specific targets only when the code truly needs them.
3. Keep explicit fallback paths outside the family.
