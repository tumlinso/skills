# Hopper Profiling Interpretation

Use this route when the first problem is reading Nsight output on H100-class
hardware.

## Ask First

- did TMA shift the kernel away from copy overhead
- did clustered execution reduce global traffic enough to matter
- did FP8 or Tensor Core routing actually fire
- is the kernel now limited by cluster sync, memory, or occupancy
