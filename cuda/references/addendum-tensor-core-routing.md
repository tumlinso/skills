# Tensor Core Routing For Volta V100

Use this addendum when dense or blocked work on Tesla V100 16 GB `sm_70` should probably be using Tensor Cores, but the current path is not delivering the expected throughput.

This file is the operational route. It should answer:

- is the workload eligible for Tensor Core pursuit
- what the fastest library-backed route is
- what to fix before low-level kernel work
- how to verify that Tensor Cores are really firing
- when to escalate into WMMA, CUTLASS specialization, or PTX-level work

## Core Rule

Push dense and reformulable blocked work toward Tensor Core execution by default.

If the request is for a custom op on Volta and the dominant inner loop is
Tensor Core-eligible, route here early instead of treating Tensor Core work as
an optional follow-on.

Do not stop at "FP16 is enabled" or "power is lower than expected." First prove:

- the math path is eligible
- the shapes and blocking are Tensor Core-friendly
- the library path is correct
- the profiler evidence agrees

If all four are true and the gap is stable, then escalate to low-level work.

## 1. Eligibility Triage

Pursue Tensor Cores aggressively when the hot region is one of these:

- GEMM or batched GEMM
- grouped projections
- attention score or projection blocks that still map to matrix math
- blocked sparse formats such as blocked ELLPACK where the real work is dense tile math
- fused kernels whose dominant inner loop is still tiled matrix multiply-accumulate

For sparse Tensor Core work, strongly prefer a blocked ELLPACK-style layout over ad hoc sparse layouts when the block structure is real enough to preserve stable dense tiles. On V100, this is usually the clearest sparse layout for feeding Tensor Core-style blocked SpMM efficiently.

Do not force Tensor Core thinking first when:

- bytes moved dominate
- the hot path is mostly gather, scatter, filtering, compaction, or reduction glue
- the sparse structure is too irregular to preserve a useful dense tile boundary
- the problem is clearly launch-bound rather than math-bound

If unclear, use Nsight Compute on the hot kernel and read the summary before changing code.

## 2. Default Optimization Ladder

Use this order:

1. cuBLAS for clean GEMM-shaped work
2. cuBLASLt when epilogues, workspace, or algorithm choice matter
3. CUTLASS `Sm70` when the workload is still tiled matrix math but needs more control
4. WMMA or Volta intrinsics when the fused or blocked shape is stable and library paths leave a real gap
5. PTX-level specialization only when the kernel is stable, benchmarked end-to-end, and worth owning

Reject handwritten Tensor Core code if the library path has not been benchmarked yet.

For Volta custom-op work, use the library baseline to validate the mapping, but
keep the library path available when it is still the cleanest answer and
escalate earlier than on newer families once fixed blocked layout ownership,
fused tile control, or repeated library glue is the real reason to own the op.

## 3. Volta Enablement Rules

For Tensor Core-eligible work on `sm_70`:

- use FP16 inputs when numerically acceptable
- accumulate in FP32 when needed
- align or block key dense dimensions to multiples of 8
- batch or group small matmuls instead of launching many tiny kernels
- preserve a dense-tile boundary through packing, blocking, or reformulation when that is the real route to throughput

Do not assume:

- TF32
- BF16 Tensor Core fast paths
- Ampere sparse acceleration
- `cp.async`

On V100, awkward exact dimensions often lose to lightly padded Tensor Core-friendly ones. Benchmark the padded path before protecting exact shapes.

## 4. Verification Workflow

When a dense or blocked path should be on Tensor Cores:

1. establish a clean cuBLAS or cuBLASLt baseline when possible
2. run Nsight Compute on the representative steady-state kernel
3. read the summary first
4. check section-level evidence for Tensor Core use, math-pipeline saturation, and whether bytes moved still dominate
5. compare throughput, not just one counter

Interpretation rules:

- weak Tensor Core activity on dense FP16 work is usually a routing or shape problem first
- strong Tensor Core activity with weak end-to-end speedup often means the surrounding glue is the real bottleneck
- board power near the top of the V100 envelope is supporting evidence for eligible dense large-compute runs, not proof by itself

## 5. Reformulation Rules

Be willing to reformulate when the end-to-end path benefits:

- pad hidden widths, tile sizes, or projection widths to Tensor Core-friendly multiples
- convert many tiny GEMMs into grouped or batched calls
- repack blocked sparse data into dense tiles when the packing cost is amortized by much faster tile math
- prefer blocked ELLPACK-style storage when sparse SpMM is really a blocked dense-tile problem and the metadata cost stays controlled
- fuse only the glue that preserves the Tensor Core-friendly core instead of overfusing the whole path

Reject reformulations that:

- add more data movement than the Tensor Core win repays
- make a memory-bound path denser without reducing passes
- destroy steady-state residency or create heavy host-visible staging

## 6. Escalation Rules

Escalate to `references/volta-tensor-core-low-level.md` only when:

- the workload is clearly Tensor Core-eligible
- the benchmark window is representative
- the cuBLAS, cuBLASLt, or CUTLASS path is already correct
- the remaining gap is stable across repeated runs

For explicit Volta custom-op requests, the stable gap may be throughput,
avoidable epilogue or packing overhead, or the cost of keeping the op split
across too many library launches.

When escalating, state explicitly:

- why the library path is insufficient
- what fixed tile or blocked structure justifies owning the kernel
- whether the goal is higher math throughput, less glue overhead, or both

## 7. Output Requirements

Be explicit about:

- whether the advice assumes Tesla V100 `sm_70`
- why the workload is or is not Tensor Core-eligible
- whether the route is cuBLAS, cuBLASLt, CUTLASS, WMMA, or lower-level custom
- whether a Volta custom op should stay library-backed or own the Tensor Core
  kernel earlier
- what padding, blocking, batching, or grouping change is needed
- whether profiler evidence or end-to-end results show the current path is still compute-limited
- whether power draw supports the conclusion without replacing profiler evidence
