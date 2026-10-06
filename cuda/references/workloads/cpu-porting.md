# Porting CPU-Centric Work To CUDA

Use this guide when the code still reflects CPU caches, thread pools, object graphs, serial stages, or callback-sized tasks. Do not map those structures literally onto CUDA: choose the execution model, data layout, and residency boundary before tuning kernels.

Use the [porting decision tree](cpu-porting-decision-tree.md) when the right
endpoint remains unclear after identifying the hot phase and its data movement.

## Choose the endpoint

- **Directive offload** fits regular loop nests with simple dependencies and stable data regions. Compare OpenMP target, OpenACC, and NVHPC only after checking data movement and abstraction overhead.
- **Library-backed CUDA** fits dense or primitive-shaped phases. Check cuBLAS/cuBLASLt, cuSPARSE, CUB/CCCL, and related libraries before writing a kernel; see [compute-library routing](../common/compute-libraries.md).
- **Native CUDA** fits irregular, sparse, glue-heavy, or repeatedly staged work whose decomposition/layout must change.
- **Mixed execution** fits a pipeline where only selected hot phases need explicit CUDA and small or control-heavy phases remain cheaper on CPU.

CPU-centric warning signs include AoS or pointer-rich graphs, serial loop dependencies, CPU-sized task queues, tiny virtual/callback work units, repeated host-visible staging, and sparse traversals that combine layout, filtering, and arithmetic in one serial flow. These usually call for a new work unit (row, tile, element, block, or reduction), flattened/SoA data, explicit sparse formats, and a device-resident pipeline before micro-tuning.

For a native or mixed rewrite, use [rewrite patterns](cpu-to-cuda-rewrite-patterns.md) to restructure work, layout, and stages. For sparse scientific or biological matrices, first classify row-wise versus feature-wise phases in [sparse bio layout](sparse-bio.md), then use [CPU-to-sparse porting](cpu-porting-sparse-bio.md). If directive offload is a serious endpoint, compare its overhead with [NVHPC guidance](../specialized/nvhpc.md).

Keep work on CPU when it is tiny, truly control-heavy, and transfer/launch costs exceed its repeated value. Move it to GPU when data is already resident, work repeats, staging disappears, or the phase becomes a clean library/kernel primitive. Do not optimize device code before fixing CPU-shaped decomposition, layout, and residency.
