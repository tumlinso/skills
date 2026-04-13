# CUDA Follow-On

Use this reference when a comparison already shows a CUDA-specific hotspot and the next question is deeper GPU diagnosis rather than comparative harnessing.

## Route Rule

Stay in `compare-benchmarks` when the main question is:

- are A and B being compared fairly
- which phase differs
- whether the profiler evidence is sufficient

Route into `cuda-v100` when the main question becomes:

- why one CUDA implementation is slower at the kernel or topology level
- whether Tensor Cores, sparse formats, fusion, PTX, or CPU-to-CUDA porting choices are the real cause

## Required Handoff Information

Before routing into `cuda-v100`, have:

- the comparison summary
- the dominant phase or component
- the profiler summary if available
- the correctness status

Do not route into `cuda-v100` merely because the compared implementations happen to use GPUs.
