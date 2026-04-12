# Extreme CUDA/C++ Optimization Guide For Tesla V100 16GB (`sm_70`)

## Scope

Use this file for concrete implementation choices:

- build flags
- CMake settings
- profiler commands
- Volta-specific kernel rules
- CUTLASS / cuBLAS / cuBLASLt / cuSPARSE / NCCL usage
- libtorch / ATen integration

Read `v100_programming_guide.md` first for topology and optimization order.

If the question is specifically how to get dense or blocked work onto Tensor Cores, read `references/addendum-tensor-core-routing.md` before owning low-level WMMA or PTX code.

## Quick Map

- `1. Build Rules`
- `2. Fastest Full-Path Rule`
- `3. Volta Kernel Rules`
- `4. Profiling Commands`
- `5. Dense Math Patterns`
- `6. Sparse And Irregular Work`
- `7. Multi-GPU Implementation Rules`
- `8. Streams, Copies, And CUDA Graphs`
- `9. Launch Heuristics`
- `10. Libtorch / ATen Rules`
- `11. Decision Tree`

## 1. Build Rules

### 1.1 Toolchain

- use CUDA 12.x for native Volta builds
- compile exactly for `sm_70`
- do not ship vague multi-arch builds when the deployment target is known

### 1.2 Benchmark Build

```bash
nvcc -O3 \
  -std=c++17 \
  -arch=sm_70 \
  -lineinfo \
  -Xptxas=-v \
  -Xcompiler=-fno-omit-frame-pointer \
  -DNDEBUG \
  your_file.cu -o your_bin
```

### 1.3 Aggressive Release Build

```bash
nvcc -O3 \
  -std=c++17 \
  -arch=sm_70 \
  -lineinfo \
  -Xptxas=-v \
  --use_fast_math \
  -DNDEBUG \
  your_file.cu -o your_bin
```

Use `--use_fast_math` only when the numerical tradeoff is acceptable.

### 1.4 CMake Skeleton

```cmake
cmake_minimum_required(VERSION 3.24)
project(v100_extreme LANGUAGES CXX CUDA)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CUDA_STANDARD 17)
set(CMAKE_CUDA_ARCHITECTURES 70)

add_executable(v100_main main.cu)

target_compile_options(v100_main PRIVATE
  $<$<COMPILE_LANGUAGE:CUDA>:-O3 --use_fast_math -lineinfo -Xptxas=-v>
)

target_link_libraries(v100_main PRIVATE
  cublas
  cublasLt
  cudnn
  cusparse
  cutensor
  nccl
)
```

## 2. Fastest Full-Path Rule

Start from a library path when the mapping is clean. Escalate to fused custom kernels when:

- the operation is not expressible as GEMM, convolution, contraction, or sparse primitive
- library composition adds too many HBM passes
- launch overhead dominates because the kernels are tiny and repeated
- the workload shape is specialized enough that fixed kernels can beat general heuristics
- you need fused behavior the library path cannot provide

If the current decomposition is slow but convenient, change the decomposition.

### 2.1 Preferred Libraries

- cuBLAS: default dense math
- cuBLASLt: fused epilogues, algorithm choice, workspace tuning
- CUTLASS: matrix math with more control than cuBLASLt exposes
- cuDNN: standard DNN primitives
- cuTENSOR: large contractions and tensor reductions
- cuSPARSE: sparse primitives
- NCCL: multi-GPU collectives and point-to-point on CUDA tensors

## 3. Volta Kernel Rules

### 3.1 Warp Rules

Use `_sync` intrinsics:

- `__shfl_down_sync`
- `__ballot_sync`
- `__syncwarp`

Never rely on implicit warp lockstep.

### 3.2 Throughput, Not Occupancy

Do not maximize occupancy blindly. On V100, faster kernels often win with:

- more registers
- better ILP
- fewer spills
- larger useful tiles

Use Nsight Compute to decide whether occupancy or register pressure is the actual limiter.

### 3.3 Memory Rules

- HBM is fast enough to reward fusion, but repeated full-memory passes still hurt badly
- PCIe is slow enough to dominate entire programs
- registers are precious
- shared memory is useful only when it reduces real traffic or enables reuse
- local memory in hot kernels usually means spills, not "free private scratch"
- constant memory is useful for warp-uniform read-mostly parameters, not scattered lane-varying reads

### 3.4 Shared Memory Rule

- above 48 KB per block requires explicit opt-in
- compare heavy shared-memory designs against lighter variants
- do not use shared memory when L1 and registers already cover the reuse pattern

### 3.5 Vectorization Rule

Vectorize loads and stores whenever alignment and access patterns allow it. But do not force vectorization through misaligned or divergent access.

### 3.6 Reduction Rule

Use shuffle for warp-local reductions. Use shared memory only when the reduction crosses warp boundaries.

### 3.7 Divergence Rule

Do not treat every branch as a reason to split the kernel.

Prefer one kernel with moderate divergence when:

- branch bodies are short
- the alternative adds obvious launch trains
- the alternative adds extra full-memory passes

Prefer specialization or multiple kernels when:

- branch bodies are long and materially different
- branch-specific memory access patterns are also different
- one class of work is consistently heavier than another

### 3.8 Over-Fusion Rule

If fusion raises registers/thread sharply, introduces local-memory traffic, or forces heavy shared-memory carveout, the fusion depth may be wrong.

### 3.9 Memory-Tier Rule

Use:

- registers for short-lived intermediates
- shared memory for real cooperative reuse
- cached global memory when reuse is weak and a shared-memory tile buys little
- constant memory for warp-uniform metadata

Do not assume moving data into shared memory is automatically better than letting L1/L2 serve the access pattern.

## 4. Profiling Commands

### 4.1 Nsight Systems

Use this first to find:

- memcpy dominance
- launch trains
- allocator churn
- synchronization bottlenecks
- overlap failures

```bash
scripts/profile_nsys.sh \
  --label run_nsys \
  ./your_bin
```

Read `summary.txt` first. If it says the run is not representative of steady state, fix the run window before tuning kernels.

### 4.2 Nsight Compute

Use this on the hot kernel to inspect:

- memory vs compute saturation
- Tensor Core usage on dense work
- register pressure
- shared-memory cost
- occupancy limits

```bash
scripts/profile_ncu.sh \
  --launch-count 20 \
  ./your_bin
```

Read `summary.txt` first. If it says `counter_valid: yes`, trust the limiter classification. Do not trust the profiled runtime for throughput timing.

## 5. Dense Math Patterns

### 5.1 cuBLAS Rule

If the operation looks like GEMM, batched GEMM, grouped GEMM, or dense projection, benchmark cuBLAS before touching custom CUDA.

Use FP16 inputs with FP32 accumulation where acceptable. Align dimensions to multiples of 8.

### 5.2 cuBLASLt Rule

If the path is:

- GEMM -> bias
- GEMM -> bias -> GELU
- GEMM -> bias -> ReLU

benchmark cuBLASLt before writing a custom epilogue.

Minimal pattern:

```cpp
cublasLtHandle_t lt;
cublasLtCreate(&lt);

// Build matmul desc + matrix layouts + preference.
// Set epilogue and bias pointers when needed.
// Query heuristics.
// Run cublasLtMatmul with a real workspace.
```

### 5.3 WMMA Rule

Use handwritten WMMA only when:

- CUTLASS is too inflexible for the case
- the kernel is stable enough to tune by hand
- the surrounding fused logic is the real reason to own the kernel

### 5.4 CUTLASS Rule

Use CUTLASS when the work is still tiled matrix math but you need:

- custom tile shapes
- custom epilogues
- architecture-specific specialization

For Volta, use `Sm70` kernels and benchmark them against cuBLASLt before committing.

## 6. Sparse And Irregular Work

### 6.1 Do Not Freestyle Primitive-Shaped Sparse Work

Use cuSPARSE first for:

- SpMV
- SpMM
- SpGEMM
- SDDMM

### 6.2 Escalate When The Glue Is The Problem

Use custom fused kernels early when time is dominated by:

- indexing
- remapping
- filtering
- compaction
- irregular reduction glue
- format conversion plus follow-on passes

### 6.3 CUB / CCCL Rule

Use CUB / CCCL for:

- scans
- segmented scans
- segmented reductions
- sorting
- select / compaction

Do not rewrite these primitives unless the fused full path justifies it.

## 7. Multi-GPU Implementation Rules

### 7.1 Rank Placement

Treat the true fast groups as:

- logical pair A = `0,2`
- logical pair B = `1,3`

When possible, reorder visible devices so software sees the fast pairs contiguously.

### 7.2 Communication Rule

- heavy traffic stays inside each NVLink pair
- cross-pair traffic is coarse-grained
- pair-local reduction happens before cross-pair exchange
- avoid `SYS` edges for steady-state traffic

### 7.3 NCCL Rule

Use NCCL for collectives and topology-aware communication. Benchmark before setting:

- `NCCL_ALGO`
- `NCCL_PROTO`
- `NCCL_P2P_LEVEL`

### 7.4 One-Process-Per-GPU Rule

Because the fast pairs cross NUMA domains, one process per GPU is usually the safest host-side default for communication-heavy workloads.

## 8. Streams, Copies, And CUDA Graphs

### 8.1 PCIe Discipline

- use pinned memory for unavoidable copies
- batch small copies into larger ones
- keep steady-state tensors on device

### 8.2 Stream Rule

Use multiple streams only when you have real overlap to exploit. Do not add streams that only increase synchronization complexity.

### 8.3 CUDA Graph Rule

Use CUDA Graph capture when:

- the steady-state step repeats many times
- the launch graph is stable
- many small kernels remain after obvious fusion

Minimal capture pattern:

```cpp
cudaStreamBeginCapture(stream, cudaStreamCaptureModeGlobal);
// enqueue steady-state work
cudaStreamEndCapture(stream, &graph);
cudaGraphInstantiate(&graph_exec, graph, nullptr, nullptr, 0);
cudaGraphLaunch(graph_exec, stream);
```

## 9. Launch Heuristics

Good starting points:

- memory-bound pointwise kernels: 128 to 256 threads/block
- reductions: warp-aware layouts first, then block sizes 128 to 256
- GEMM-like custom kernels: choose tile sizes from register and shared-memory budgets, not from occupancy folklore

Then tune from profiler output.

## 10. Libtorch / ATen Rules

### 10.1 High-Level Interface, Low-Level Speed

Use libtorch / ATen for integration, not as an excuse to keep a slow backend path.

Rules:

- keep tensor layout choices explicit
- use the current CUDA stream
- call cuBLAS, cuBLASLt, cuSPARSE, or NCCL directly when that is the fastest backend
- do not write a bad custom GEMM because the op is wrapped in PyTorch

### 10.2 Current-Stream Pattern

```cpp
cudaStream_t stream = at::cuda::getDefaultCUDAStream();
// or current stream from the runtime / framework context
```

### 10.3 Custom Op Rule

If a custom op is mostly:

- dense math
- sparse primitive dispatch
- communication

call the optimized library from the op instead of replacing it with inferior handwritten CUDA.

## 11. Decision Tree

If it looks like dense linear algebra:

- use cuBLAS or cuBLASLt

If it looks like tensor contraction:

- use cuTENSOR

If it looks sparse and primitive-shaped:

- use cuSPARSE and CUB

If it is mostly pointwise or reduction glue:

- consider `references/addendum-kernel-mechanics.md`
- fuse it
- reduce memory passes
- consider CUDA Graph capture

If it needs multi-GPU:

- keep heavy traffic inside `0<->2` and `1<->3`
- use NCCL
- reduce locally before crossing pairs

## Official References

- Volta tuning guide: https://docs.nvidia.com/cuda/volta-tuning-guide/index.html
- CUDA release notes: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html
- cuBLAS / cuBLASLt: https://docs.nvidia.com/cuda/cublas/index.html
- cuSPARSE: https://docs.nvidia.com/cuda/cusparse/index.html
- Nsight Compute profiling guide: https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html
