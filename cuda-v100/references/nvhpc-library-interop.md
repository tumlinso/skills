# Library Interop

## Preferred Pattern

Use NVHPC surfaces around the edges of the program only if the hot path still calls the right CUDA libraries explicitly.

Good interop targets:

- cuBLAS / cuBLASLt
- cuSPARSE
- NCCL
- NVTX

## Rule

Do not replace a strong library call with a weaker directive or stdpar path just to make the source look cleaner.

## Profiling Rule

Keep NVTX ranges explicit when possible so Nsight Systems and Nsight Compute still tell you where the time is going.

## Dense Math

If the real work is GEMM or GEMM plus epilogue, keep the cuBLAS/cuBLASLt path explicit.

## Sparse Math

If the real work is SpMV / SpMM / segmented reduction / sparse glue, keep cuSPARSE and custom-kernel integration explicit.

## Communication

If communication matters, keep NCCL explicit and topology-aware. Do not let an abstraction flatten away rank layout and stream semantics.
