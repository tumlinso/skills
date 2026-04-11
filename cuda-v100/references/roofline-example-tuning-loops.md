# Example Tuning Loops

## Example 1: Memory-Bound Fused Sparse Glue Kernel

Observed:

- Nsight Compute shows high DRAM pressure
- SM throughput is modest
- occupancy changes do not move end-to-end time much

Loop:

1. confirm the kernel is actually hot in end-to-end time
2. count the full-memory passes before and after the kernel
3. remove one intermediate write if possible
4. re-measure DRAM pressure and total step time
5. only if still hot, test coalescing or vectorized access changes

Stop when:

- DRAM traffic is near the practical wall
- another stage becomes dominant
- further occupancy work does not change step time

## Example 2: Dense Volta Kernel With Weak Tensor Core Use

Observed:

- dense FP16 path
- low Tensor Core activity
- awkward dimensions

Loop:

1. benchmark cuBLAS or cuBLASLt baseline
2. pad to multiples of 8
3. compare padded vs exact-shape time
4. if the custom path still matters, revisit tile shape and register pressure

Stop when:

- library baseline wins clearly
- or the custom kernel closes the gap and the remaining bottleneck is elsewhere

## Example 3: Launch-Bound End-To-End Path

Observed:

- many short kernels
- good individual metrics, poor overall throughput

Loop:

1. identify repeated short-kernel train in Nsight Systems
2. fuse adjacent kernels where data reuse is obvious
3. replace repeated small library calls with grouped or batched variants when possible
4. capture the steady-state loop with CUDA Graphs
5. compare launch count and total step time

Stop when:

- end-to-end step time improves materially
- launch overhead is no longer the dominant wall

## Stopping Rule

Do not keep tuning the current kernel once:

- another stage dominates
- the library path is clearly better
- the kernel has reached the wrong ceiling and needs a decomposition change instead
