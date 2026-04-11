# Case Notes

## Case 1: Dense Math Still Owned By cuBLASLt

Situation:

- C++ codebase
- dense GEMM-heavy hot path
- desire for simpler integration

Good answer:

- keep cuBLASLt explicit
- let NVHPC own the surrounding build/runtime only if it does not hide data movement

Bad answer:

- replacing the explicit library path with a prettier offload abstraction that loses epilogue or workspace control

## Case 2: Sparse Irregular Path

Situation:

- CSR or CSC data
- irregular gather/scatter
- fused sparse preprocessing

Good answer:

- raw CUDA/C++ or explicit library plus custom kernels

Bad answer:

- stdpar or directive offload on the hot irregular path without proof it preserves control and movement discipline

## Case 3: Non-Critical Regular Loop

Situation:

- regular loop nest
- not the dominant runtime

Good answer:

- OpenACC or OpenMP target may be acceptable if it keeps engineering velocity high and measured overhead is small

## Case 4: Hidden Memory-Mode Cost

Situation:

- code works functionally
- performance is unexpectedly poor

Likely issue:

- managed or unified memory behavior is introducing movement or runtime overhead not visible in the source structure

Action:

- compare against explicit ownership and movement
- profile before accepting the abstraction
