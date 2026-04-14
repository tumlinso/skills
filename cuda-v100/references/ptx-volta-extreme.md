# Volta-Extreme PTX For Tesla V100 `sm_70`

Use this file only when PTX guidance was explicitly requested and the target is genuinely locked to Tesla V100 `sm_70`.

Assume throughout:

- Tesla V100 16 GB
- native Volta `sm_70`
- CUDA 12.x-era toolchain and docs

This file is for extremely hot, stable kernels where the algorithm boundary is already right and the remaining question is how to inspect or shape the Volta instruction path.

## Quick Map

- `1. Baseline Rule`
- `2. Extract The Hot Path First`
- `3. Volta Facts That Matter`
- `4. Occupancy, Registers, And Shared Memory`
- `5. Independent Thread Scheduling Correctness`
- `6. Memory-Side PTX Patterns`
- `7. ILP And Inner-Loop Shape`
- `8. Warp-Local Exchange`
- `9. Tensor Core PTX Boundaries`
- `10. Practical Inspection Loop`
- `11. Common V100 Mistakes`

## 1. Baseline Rule

On V100, “extremely optimized PTX” means PTX that lowers cleanly to Volta SASS. PTX is not the final ISA.

Treat these as non-negotiable:

- target `sm_70`
- keep an `sm_70` cubin in the workflow
- inspect the resulting SASS, not just the PTX text
- check register and shared-memory use after every structural change

If the build only emits older virtual targets, the result can miss Volta-specific features. That is especially important for Tensor Core work.

## 2. Extract The Hot Path First

Default structure for PTX work:

- put the hot primitive in a separate header or narrow translation unit
- keep the dump target to one kernel or one micro-primitive
- inspect only the named symbol when possible

Do this because:

- PTX and SASS for whole libraries are too noisy to reason about
- model context is better spent on the hot path than on unrelated glue
- small isolated kernels make it obvious whether a rewrite helped or only moved instructions around

Good shapes:

- one `*.cuh` header that owns the inner loop
- one `*.cu` file that exists only to compile or disassemble the hot kernel
- one standalone `.ptx` file for a fixed micro-primitive
- one generated focused `.cu` from `scripts/split_cuda_translation_unit.py` when the original source contains multiple kernels

Bad shapes:

- dumping PTX for a giant translation unit just to inspect one warp primitive
- embedding large Volta-specific PTX blocks across many files
- asking the model to inspect full-library disassembly when a focused harness would do

Use `scripts/dump_ptx_hotspot.sh` for this workflow. Give it a focused source file and a symbol filter whenever possible.
Use `scripts/split_cuda_translation_unit.py` first when the hot kernel still lives in a multi-kernel `.cu`.

## 3. Volta Facts That Matter

These hardware facts should shape the PTX, not folklore from newer or older GPUs:

- each SM has 4 warp schedulers
- dependent core FMA latency is 4 cycles
- Volta can issue independent instructions every cycle
- FP32 and INT32 execution resources are separate
- the SM still tops out at 64 resident warps and 64K 32-bit registers
- the register ceiling is 255 per thread
- shared memory is 96 KB per SM

Practical meaning:

- expose independent work in the hot loop
- overlap INT32 address generation with FP math when the kernel is compute-shaped
- do not chase occupancy blindly when register spills are the real cost

## 4. Occupancy, Registers, And Shared Memory

Volta still rewards balance more than maximum theoretical occupancy.

Remember:

- register allocation is rounded per warp
- `32` registers per thread is the clean theoretical point for `2048` resident threads, not a universal target
- the larger unified L1 and shared/texture cache changes the spill tradeoff relative to older architectures

Starting point:

- begin around `128` to `256` threads per block
- tune register count, unroll depth, and shared-memory use together
- reject register caps that merely replace pressure with spills or extra instructions

Treat dynamic shared memory carefully:

- static shared memory stays capped at `48 KB` per block
- going above that requires explicit dynamic shared-memory opt-in
- above `48 KB`, make sure the reuse is real enough to justify the residency loss

## 5. Independent Thread Scheduling Correctness

Volta broke old warp-lockstep assumptions.

Rules:

- use `shfl.sync.*` instead of legacy shuffle forms
- use `bar.warp.sync` or `__syncwarp()` when lanes communicate through memory within a warp
- make sure every non-exited thread that should reach `bar.sync` or `__syncthreads()` actually gets there

Do not treat PTX predication as a correctness substitute for missing synchronization.

## 6. Memory-Side PTX Patterns

For memory-bound PTX, optimize access shape before instruction cleverness.

Prefer:

- coalesced accesses first
- vector loads and stores when alignment is real
- warp-uniform read-only loads only when the address is actually uniform across the warp

Useful PTX surfaces on V100:

- `ld.global.v4.f32` and similar vector forms when alignment and layout support them
- `ldu.global` for warp-uniform read-only addresses
- `ld.global.nc` only as a benchmarked experiment for read-only streaming traffic
- `prefetch.global.L1` or `.L2` only after profiling shows a real latency-hiding opportunity

Do not widen loads through misalignment or divergent addresses just because the PTX looks cleaner.

## 7. ILP And Inner-Loop Shape

For CUDA-core compute kernels, shape the hot loop around Volta’s 4-cycle arithmetic latency and FP32 plus INT32 overlap.

Prefer loop bodies with:

- multiple independent accumulators
- current math interleaved with next-address generation
- explicit `fma.rn.f32` in hot FP32 loops when you want the intent to stay obvious

Volta-shaped inner-loop sketch:

```ptx
ld.global.v4.f32  {x0, x1, x2, x3}, [px];
ld.global.v4.f32  {y0, y1, y2, y3}, [py];

add.s64           px, px, stride;
add.s64           py, py, stride;

fma.rn.f32        acc0, x0, y0, acc0;
fma.rn.f32        acc1, x1, y1, acc1;
fma.rn.f32        acc2, x2, y2, acc2;
fma.rn.f32        acc3, x3, y3, acc3;
```

The important part is the shape:

- wide coalesced load
- multiple independent accumulators
- address math overlapped with arithmetic

## 8. Warp-Local Exchange

Keep warp-local reductions, scans, and tiny transposes in registers when they fit.

Prefer:

- `shfl.sync.*` for exchange inside one warp
- `bar.warp.sync` when warp lanes exchange through memory
- shared memory only when the exchange genuinely crosses warp boundaries

Simple reduction idiom:

```ptx
shfl.sync.down.b32 t, v, 16, 0x1f, 0xffffffff;
add.f32            v, v, t;
shfl.sync.down.b32 t, v, 8,  0x1f, 0xffffffff;
add.f32            v, v, t;
```

That keeps the traffic in registers and avoids a CTA-wide barrier.

## 9. Tensor Core PTX Boundaries

For matrix-shaped work on V100, do not force a CUDA-core path if Tensor Cores are the right answer.

Use PTX-level Tensor Core work only when:

- the workload is genuinely dense or blocked enough to merit Tensor Core pursuit
- the library or CUTLASS path is already correct and still leaves a stable gap
- the question is really about low-level instruction shape rather than layout, padding, or blocking

Volta-specific reminders:

- `wmma` PTX requires `sm_70+`
- `mma.sync.m8n8k4` is the Volta-friendly low-level form to keep in mind
- CUTLASS-style hierarchical tiling, shared-memory staging, and software pipelining remain the right structural model for GEMM-like kernels

If dense math still maps cleanly to cuBLAS, cuBLASLt, or CUTLASS, use those first.

## 10. Practical Inspection Loop

First choice:

```bash
scripts/split_cuda_translation_unit.py \
  --symbol kernel_beta \
  --out-dir split_out \
  assets/ptx-examples/multi_kernel_unit_example.cu

scripts/dump_ptx_hotspot.sh \
  --label inline_hot_path \
  --symbol kernel_beta \
  split_out/multi_kernel_unit_example-kernel_beta/focused_source.cu
```

That wrapper is the preferred low-context path because it:

- targets `sm_70` by default
- captures PTX, cubin, resource usage, `cuobjdump`, and `nvdisasm`
- emits `summary.txt` and `summary.json`
- keeps focused artifacts for the requested symbol when possible

Raw command loop when the wrapper is not enough:

```bash
nvcc -arch=sm_70 --resource-usage -Xptxas=-v -cubin hot_kernel.cu -o hot_kernel.cubin
cuobjdump -sass hot_kernel.cubin
nvdisasm hot_kernel.cubin
```

Use Nsight Compute after inspection to decide whether the next edit should target:

- memory throughput
- dependency stalls
- register pressure
- occupancy

Do not keep editing PTX based only on how the source text looks.

## 11. Common V100 Mistakes

- compiling for an older virtual target and expecting Volta-specific behavior
- capping registers just to inflate occupancy, then paying in spills or extra instructions
- assuming warp-synchronous behavior without `*_sync`
- dumping or sharing monolithic PTX when the hot path could be isolated first
- overusing shared memory without checking whether Volta’s cache hierarchy already narrowed the benefit
- forcing PTX onto kernels whose real problem is layout, binning, fusion, or library choice

## 12. Official References

- Volta Tuning Guide: https://docs.nvidia.com/cuda/volta-tuning-guide/
- PTX ISA: https://docs.nvidia.com/cuda/parallel-thread-execution/
- Inline PTX Assembly Application Note: https://docs.nvidia.com/cuda/inline-ptx-assembly/
- CUDA C++ Programming Guide: https://docs.nvidia.com/cuda/cuda-c-programming-guide/
- CUDA C++ Best Practices Guide: https://docs.nvidia.com/cuda/cuda-c-best-practices-guide/
