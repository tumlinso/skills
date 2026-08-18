# Ampere Profiling Interpretation

Use this route when the first problem is reading Nsight output on A100-class
hardware.

Primary source:
https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html

## Ask First

- did async staging actually reduce register pressure
- did the kernel route onto Tensor Cores
- is L2 reuse strong enough to justify the current tile plan
- is the kernel still bound by full-memory passes instead of math

## Readouts To Prioritize

- register count and spill traffic
- Tensor Core activity for TF32 or BF16 routes
- global versus shared-memory instruction mix
- launch count and overlap for fragmented pipelines
