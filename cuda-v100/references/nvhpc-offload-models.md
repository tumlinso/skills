# NVHPC Offload Models

## NVC++ With Explicit CUDA Interop

Best fit when:

- the codebase is C++
- explicit CUDA kernels or library calls still own the hot path
- you want compiler/toolchain integration without surrendering control

## OpenACC

Potential fit when:

- the loop structure is regular enough
- the performance target is high but not absolute peak

Risk:

- hidden data movement
- less control over irregular sparse kernels

## OpenMP Target

Potential fit when:

- portability matters
- the code structure maps cleanly

Risk:

- offload/runtime overhead and reduced explicitness in exactly the places V100 tuning often needs control

## stdpar

Potential fit when:

- the algorithm is regular
- developer speed matters more than absolute control

Risk:

- memory-mode assumptions and hidden movement can be expensive

## Performance Rule

If the path is sparse, irregular, topology-sensitive, or fused-kernel-heavy, assume raw CUDA/C++ is still the benchmark to beat.
