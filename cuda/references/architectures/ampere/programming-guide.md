# Ampere Programming Guide

Use for overall A100-class strategy or when a measured bottleneck points to
Ampere-specific staging, memory behavior, Tensor Core routing, or kernel
structure. Assume `sm_80` unless the actual device says otherwise.

Primary source: [Ampere Tuning Guide](https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html).
For structured sparsity, also consult [cuSPARSELt](https://docs.nvidia.com/cuda/cusparselt/index.html).

## Family changes and baseline

- Async global-to-shared copy (`cp.async`) and split arrive-wait barriers change
  staging and producer-consumer pipelines.
- Larger L2 changes reuse decisions; it does not remove persistent-buffer
  budgeting or make HBM traffic free.
- TF32 raises the default dense-math floor. BF16 and FP16 are options only when
  the numerical budget permits them.
- 2:4 structured sparsity is a separate, opt-in path: use it only when the
  contract holds and measurement justifies it.
- Prefer an `sm_80`-only build while tuning. Revisit Volta fusion that existed
  only to hide copy latency.
- Push dense math through cuBLASLt, CUTLASS, or cuDNN before hand-tuning.

## Choose a direction from evidence

### Pipeline starvation

Prove that the GPU is starved with Nsight Systems. Classify the cause as loader,
collation, pinned-memory, copy fragmentation, or NUMA trouble; fix batching and
overlap before changing kernels. Revisit `cp.async` only after the device path
is representative.

### Kernel structure and staging

Replace manual copy ladders with `cp.async` only for regular access. Async
staging can remove the reason for aggressive fusion, so fuse less blindly than
on Volta. Specialize when branch shape or access patterns diverge enough to
defeat the staged pipeline.

### Hot kernel

First confirm that the benchmark window is representative. Use the measured
limiter to choose among Tensor Core eligibility, staging, memory passes, and
register pressure; change only the matching lever.

### Profiler interpretation

When reading Nsight output, ask whether async staging reduced register
pressure, whether the kernel actually routed onto Tensor Cores, whether L2
reuse supports the current tile plan, and whether full-memory passes still bind.
Prioritize register count and spill traffic, Tensor Core activity for TF32 or
BF16, the global/shared-memory instruction mix, and launch count and overlap in
fragmented pipelines. The [Ampere Tuning Guide](https://docs.nvidia.com/cuda/ampere-tuning-guide/index.html)
is the primary architecture reference.

### Memory fit and topology

Separate memory-fit trouble from communication trouble. Measure the actual
machine before committing to rank placement: PCIe A100, SXM A100, and NVSwitch
topologies differ. Keep staging and steady-state traffic on the fastest
available links. Tensor Core reformulation or structured sparsity can reduce
bytes only when the algorithm fits that path.

### Tensor Core and sparsity routing

Route dense blocked math to Tensor Core libraries when it maps cleanly. TF32 is
appropriate when acceptable for FP32-heavy dense work; choose BF16 or FP16 only
within the numerical budget. Do not force this route for sparse, irregular, or
memory-bound phases, when 2:4 structure is absent, or when bytes moved still
dominate after reformulation. Cluster choice and staging may matter more than
peak math throughput.

### PTX

Read PTX only when explicitly requested and after isolating the hot path. First
decide whether staging, Tensor Core routing, or decomposition is still the real
problem; dump only the focused symbol for `sm_80`.
