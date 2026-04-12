# Extreme V100 Optimization Guide For Diffusers / Transformers Kernels

## Scope

Use this file for system-level V100 decisions:

- topology-aware multi-GPU decomposition
- dense-library selection
- Tensor Core shape engineering
- communication strategy
- profiling order
- high-level optimization priorities

Read this first for the 4x V100 host with diagonal NVLink pairs.

For operational Tensor Core enablement, verification, and escalation, route next into `references/addendum-tensor-core-routing.md`.

For designing stress benchmarks that can actually saturate compute or transfers on this host, route into `references/benchmark-large-data.md`.

## Quick Map

- `1. Non-Negotiable Rules`
- `2. Hardware Facts That Change Decisions`
- `3. Optimization Priority Order`
- `4. Library Selection Ladder`
- `5. Tensor Core And Shape Rules`
- `6. Memory Movement Rules`
- `7. Kernel Mechanics Rules`
- `8. Custom Kernel Escalation Rules`
- `9. Multi-GPU Strategy For This Exact Host`
- `10. NCCL Rules`
- `11. Transformer / Diffuser Layout Rules`
- `12. Profiling Workflow`
- `13. Anti-Patterns`
- `14. Compact Playbook`

## 1. Non-Negotiable Rules

1. Choose the fastest Volta path, not the most literal implementation.
2. Treat PCIe 3.0 as the enemy.
3. Keep heavy traffic inside the real NVLink pairs: `0<->2` and `1<->3`.
4. Use FP16 Tensor Core-friendly shapes for dense math when numerically acceptable.
5. Stay on CUDA 12.x for native Volta `sm_70` builds.
6. Use custom fused kernels early when the hot path is glue-heavy, irregular, sparse, or launch-bound.
7. Tune from profiler data, not from intuition.

## 2. Hardware Facts That Change Decisions

### 2.1 GPU Facts

| Item | V100 16GB | Why it matters |
|---|---:|---|
| Compute capability | `sm_70` | Compile specifically for Volta |
| SMs | 80 | Size grids and persistent work for 80 SMs |
| Tensor Cores | 640 | Main route to peak dense throughput |
| HBM2 | 16 GB | Control working-set growth |
| HBM2 bandwidth | 900 GB/s | Local memory is fast enough to reward fusion |
| Shared memory per SM | 96 KB | Useful, but carveout and occupancy matter |
| Registers per SM | 64K 32-bit | Register pressure is a first-class limiter |
| Max warps per SM | 64 | Occupancy ceiling, not the goal |
| Independent Thread Scheduling | yes | Use `_sync` intrinsics; no implicit warp lockstep |

### 2.2 Volta Constraints

- No TF32.
- No `cp.async`.
- No BF16 Tensor Core fast path.
- No Ampere sparsity features.
- Shared memory above 48 KB per block requires explicit dynamic shared-memory opt-in.

### 2.3 PCIe, NVLink, And Host Transfer Reality

- HBM2 is about **900 GB/s**.
- NVLink on supported V100 systems is up to **300 GB/s bidirectional aggregate per GPU**.
- PCIe is only **32 GB/s bidirectional theoretical**.
- Pinned host transfers on PCIe Gen3 x16 are roughly **12 GB/s** in practice.

Operational meaning:

- do not bounce tensors through host memory
- batch transfers when transfers are unavoidable
- design for data residency first
- prefer one good fused device pass over several passes separated by host-visible steps

### 2.4 Actual Host Topology

Treat this machine as an X-shaped topology:

- fast pair: `GPU0 <-> GPU2` = NVLink
- fast pair: `GPU1 <-> GPU3` = NVLink
- acceptable leader exchange: `GPU0 <-> GPU1` = PHB
- acceptable leader exchange: `GPU2 <-> GPU3` = PHB
- worst paths: `GPU0 <-> GPU3` and `GPU1 <-> GPU2` = SYS

Rules:

- 2-GPU jobs: prefer `0,2` or `1,3`
- 4-GPU jobs: build around groups `{0,2}` and `{1,3}`
- inter-group exchange: prefer `0<->1` or `2<->3`
- avoid steady-state traffic on `SYS` paths
- do not assume ordinally adjacent GPUs are the fast pair

Because the NVLink pairs cross NUMA domains, communication-heavy work should usually use one process per GPU with local CPU affinity and NCCL for GPU communication.

## 3. Optimization Priority Order

Use this order when deciding what to change:

1. remove host↔device traffic
2. remove cross-pair traffic
3. reformulate into a high-performance library path when the mapping is clean
4. change layout, padding, batching, or grouping to unlock better kernels
5. fuse memory-bound glue work to reduce HBM passes
6. use CUDA Graph capture when the steady-state step is still launch-heavy
7. only then do instruction-level kernel tuning

If a change saves syntax or abstraction but hurts this ordering, reject it.

## 4. Library Selection Ladder

### 4.1 Dense Math

Default to:

- cuBLAS for GEMM, batched GEMM, grouped GEMM, GEMV-like dense work
- cuBLASLt when bias, activation, algorithm selection, or workspace tuning matters

Use this first for:

- linear layers
- QKV projections
- output projections
- MLP up/down projections
- attention score blocks that map cleanly to GEMM

### 4.2 Tensor Contractions

Use cuTENSOR before inventing a custom contraction kernel.

### 4.3 Convolutions And Standard DNN Blocks

Use cuDNN when the operation is already a cuDNN primitive or composition-friendly DNN block.

### 4.4 Sparse Work

Use cuSPARSE when the hot operation is actually:

- SpMV
- SpMM
- SpGEMM
- SDDMM
- sparse conversion or reorder helpers

If the real cost is the glue around those calls, optimize the full path, not the isolated primitive.

### 4.5 GEMM-Like But Not Fully Served By Libraries

Use CUTLASS before handwritten WMMA when:

- the problem is still tiled matrix math
- you need more control than cuBLASLt gives you
- the kernel shape is stable enough to justify template specialization

### 4.6 When To Escalate To Custom Fused Kernels

Escalate early when most time is spent in:

- pointwise or reduction glue around a strong library kernel
- repeated packing or layout conversion
- masking, indexing, gather/scatter, or irregular reduction logic
- many tiny kernels that cannot amortize launch overhead
- domain-specific fused passes that do not map to one primitive

## 5. Tensor Core And Shape Rules

### 5.1 Dense Math Defaults

- prefer FP16 inputs when numerically acceptable
- accumulate in FP32 where needed
- align important dimensions to multiples of 8
- batch work instead of issuing many tiny GEMMs
- group small GEMMs when possible

### 5.2 Padding Rule

On V100, padding a dense dimension to a multiple of 8 is often a net win even when it increases nominal FLOPs. Benchmark the padded path before preserving an awkward exact shape.

### 5.3 cuBLASLt Rule

If the current path looks like:

- GEMM -> bias
- GEMM -> bias -> GELU
- GEMM -> bias -> ReLU

benchmark cuBLASLt before writing a custom epilogue kernel.

### 5.4 Do Not Force Tensor Core Thinking Everywhere

Sparse, irregular, or glue-heavy phases are often memory-bound. The win there is fewer bytes moved and fewer launches, not fake Tensor Core usage.

When the workload is dense or reformulable into stable blocked dense tiles, read `references/addendum-tensor-core-routing.md` for the operational ladder before committing to low-level code.

## 6. Memory Movement Rules

### 6.1 Residency First

- keep tensors resident on the owning GPU
- avoid host round-trips between stages
- avoid cross-pair traffic in steady state

### 6.2 Host Transfer Discipline

- use pinned memory for unavoidable host transfers
- batch many small transfers into larger transfers
- overlap copy and compute when the schedule is stable
- separate setup transfers from steady-state transfers in measurements

### 6.3 HBM Discipline

HBM is fast, but repeated full-memory passes still kill throughput. Prefer:

- fused epilogues
- grouped kernels
- one-pass reductions where possible
- keeping intermediate values in registers or shared memory when reuse justifies it

### 6.4 Shared Memory Rule

Use shared memory when it reduces real traffic or enables cooperative reuse. Do not use it out of habit when the L1 path is already good enough or when carveout destroys occupancy.

## 7. Kernel Mechanics Rules

### 7.1 Fusion Rule

Prefer fusion when it removes real HBM passes or obvious launch trains.

Do not fuse by reflex when the combined kernel would:

- create long heavy divergent regions
- introduce register spills
- inflate shared-memory use without proven reuse
- destroy the regular library-shaped fast path

### 7.2 Divergence Rule

Divergence is acceptable when it is short, coherent, or cheaper than extra passes and launches.

Divergence is a problem when it is long, hot, and paired with poor memory behavior. In that case prefer:

- specialization
- binning
- preprocessing or compaction
- multiple kernels with clearer launch shapes

### 7.3 Launch-Overhead Rule

Prefer moderate divergence over a train of tiny kernels when:

- the branch bodies are short
- the alternative decomposition adds many launches
- the unfused path also adds extra memory traffic

Prefer extra launches over divergence when:

- branch bodies are long and materially different
- specialization materially improves launch geometry or memory access

### 7.4 Memory-Tier Rule

Think in this order:

- registers for short-lived fused intermediates
- shared memory only for real cooperative reuse
- HBM as the expensive fallback path for full-sized tensors
- local memory as a spill warning sign unless intentionally used

If a fusion idea increases local-memory traffic or shared-memory carveout sharply, reassess the fusion depth.

## 8. Custom Kernel Escalation Rules

Use custom kernels when:

- the operation is not primitive-shaped
- library composition introduces too many HBM passes
- launch overhead dominates
- the workload is mask-heavy, sparse, irregular, or indexing-heavy
- one fused pass can replace multiple clean but slow kernels

Kernel rules for Volta:

- use `_sync` warp intrinsics
- optimize throughput, not occupancy in isolation
- watch register pressure before chasing larger tiles
- prefer warp shuffle for warp-local reductions
- treat register capping as an experiment, not a belief
- use CUDA Graph capture when the launch train is the bottleneck

## 9. Multi-GPU Strategy For This Exact Host

### 9.1 Best 2-GPU Choices

Prefer:

- `CUDA_VISIBLE_DEVICES=0,2`
- `CUDA_VISIBLE_DEVICES=1,3`

### 9.2 Best 4-GPU Decomposition

Default mental model:

- pair-local group A = `{0,2}`
- pair-local group B = `{1,3}`

Then:

- do heavy tensor parallel or model-parallel traffic inside each pair
- do coarse-grained exchange between group leaders
- reduce inside pair before crossing pairs

### 9.3 Good Patterns

- tensor parallel inside each NVLink pair, data or pipeline parallel across pairs
- hierarchical all-reduce: pair-local first, cross-pair leaders second
- pair-local inference replicas when the model fits in two GPUs

### 9.4 Bad Patterns

- full 4-way tensor parallel ignoring the diagonal fast pairs
- rank orderings that hide the real topology
- hot traffic over `SYS`
- one CPU process trying to drive both members of an NVLink pair while remaining NUMA-local

## 10. NCCL Rules

- start with defaults; NCCL is topology-aware
- use `nccl-tests` before cargo-culting env vars
- treat `NCCL_P2P_LEVEL` as an experiment, not as permanent doctrine
- benchmark algorithm and protocol changes instead of locking them in from folklore
- communicate summaries, leaders, or reduced tensors across pairs, not large raw activations when avoidable

For this machine:

- large frequent traffic should remain inside `{0,2}` and `{1,3}`
- cross-pair traffic should be aggregated and infrequent

## 11. Transformer / Diffuser Layout Rules

- make hidden widths and intermediate sizes Tensor Core-friendly
- prefer layouts that avoid repeated transposes
- batch attention work enough to keep GEMMs healthy
- place KV cache and activations to preserve locality
- fuse residual, norm, and pointwise glue where the framework does not already do it
- if the model shape is under your control, accept some padding or width choices that produce much faster kernels

## 12. Profiling Workflow

1. verify topology with `nvidia-smi topo -m`
2. measure peer paths and NCCL behavior
3. run Nsight Systems for timeline, overlap, memcpy, allocator churn, and launch trains
   - trust the wrapper `summary.txt` before trusting the run
4. run Nsight Compute on the hot kernels
   - trust it for kernel cause, not throughput timing
5. compare against the fastest plausible alternative
6. stop tuning arithmetic when the kernel is already pinned to a memory roofline

Questions Nsight Systems should answer:

- are transfers dominating?
- is launch overhead dominating?
- is synchronization dominating?
- are there allocator or host bottlenecks?

Questions Nsight Compute should answer:

- is the kernel memory-bound or compute-bound?
- are Tensor Cores actually firing on dense FP16 work?
- is register pressure limiting residency?
- is shared-memory use worth its occupancy cost?

If the answer is "Tensor Cores should be firing but are not," route into `references/addendum-tensor-core-routing.md` before hand-tuning instruction-level details.

## 13. Anti-Patterns

- preserving awkward shapes to avoid padding
- assuming `0,1` or `2,3` are the NVLink pairs
- writing custom GEMM before benchmarking cuBLAS/cuBLASLt/CUTLASS
- routing steady-state traffic through host memory
- over-tuning NCCL env vars before topology and baseline tests
- maximizing occupancy while ignoring register spills or memory traffic
- forcing Tensor Core thinking onto sparse or irregular phases
- benchmarking a vague `large` case that is neither compute-saturating nor transfer-stressing
- splitting short branchy glue into many launches when moderate divergence would be cheaper
- keeping many tiny kernels because the decomposition looks clean in framework code

## 14. Compact Playbook

If the workload is dense:

- use cuBLAS or cuBLASLt
- pad to multiples of 8
- prefer FP16 with FP32 accumulation
- fuse epilogues

If the workload is mostly glue around dense kernels:

- fuse the glue
- reduce HBM passes
- consider CUDA Graph capture

If the workload is sparse or irregular:

- use cuSPARSE for primitive-shaped kernels
- use custom fused kernels for indexing-heavy or launch-heavy glue

If the workload is multi-GPU:

- keep heavy traffic inside `0<->2` and `1<->3`
- reduce pair-local first
- cross pairs only with coarse-grained exchange

## Official References

- Volta tuning guide: https://docs.nvidia.com/cuda/volta-tuning-guide/index.html
- CUDA best practices guide: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/index.html
- CUDA release notes: https://docs.nvidia.com/cuda/cuda-toolkit-release-notes/index.html
- cuBLAS / cuBLASLt: https://docs.nvidia.com/cuda/cublas/index.html
- Nsight Compute: https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html
- Nsight Systems: https://developer.nvidia.com/nsight-systems
