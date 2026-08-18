---
name: cuda
description: Primary CUDA skill for datacenter NVIDIA GPUs. Use for CUDA build, profiling, debugging, low-level optimization, kernel-structure decisions, memory fit, topology, host-device pipeline work, Tensor Core routing, request-only PTX guidance, CPU-to-CUDA porting, sparse scientific workloads, Torch extensions, and benchmark design on Volta/V100, Ampere/A100, Hopper/H100, Blackwell/B100-B200, and GB200 NVL72 deployments. Prefer this over the legacy `cuda-v100` shim for all active CUDA work.
---

# CUDA

Public router for datacenter CUDA work.

Use `cuda`, not `cuda-v100`, unless the user explicitly asks for the legacy
label.

If the user is choosing a model family for the native Volta machine, route
through `v100-model-design` first, then return here for implementation.

Route in this order:

1. choose system when topology or deployment shape matters
2. choose architecture family
3. choose one bottleneck route
4. read one micro-router
5. read a deep manual only if the micro-router still says unresolved

Profiler and benchmark artifacts come first. Read summaries before raw logs.

## System First

| If the task sounds like... | Start here |
| --- | --- |
| "this is my current V100 box", "optimize for my 4xV100 host", "benchmark on the native machine" | `references/systems/native.md` |
| "this will deploy on GB200 NVL72", "Grace-Blackwell topology", "deployment collectives" | `references/systems/gb200-nvl72.md` |

## Architecture Second

| If the task sounds like... | Start here |
| --- | --- |
| "V100", "Volta", "sm_70", "native path" | `references/architectures/volta/router.md` |
| "A100", "Ampere", "sm_80", "TF32", "`cp.async`", "structured sparsity" | `references/architectures/ampere/router.md` |
| "H100", "Hopper", "sm_90", "TMA", "thread block clusters", "FP8" | `references/architectures/hopper/router.md` |
| "B100", "B200", "Blackwell", "sm_100", "FP4", "GB200 deployment" | `references/architectures/blackwell/router.md` |

## Common Doctrine

Load these only for cross-family structure questions.

- `references/common/code-organization.md` for one-kernel-per-TU rules, dense
  machine-facing comments, low-level dump hygiene, and generated-code layout.
- `references/common/diagnostics-workflow.md` for summary-first profiling,
  debugging, sanitizer, and dump-filtering workflows.
- `references/common/compute-libraries.md` for choosing host-launched CUDA
  libraries, MathDx in-kernel device extensions, CUTLASS, CUB/CCCL, NCCL,
  NVSHMEM, or custom CUDA.

## Ground Rules

1. Optimize for the actual architecture.
   - Check Tensor Core eligibility before accepting a regular FP path.
   - Prefer Tensor Core-capable libraries when the mapping is clean.
   - Prefer custom CUDA when fusion removes HBM traffic, launch trains, or
     forced library glue.
   - On Volta custom-op work, escalate earlier to owned Tensor Core kernels
     once the mapping is stable and HBM-pass removal or fused tile ownership is
     the real win.
2. Keep builds and artifacts narrow.
   - Build only the target architecture while tuning.
   - Keep one hot kernel per TU when dump or profiler work is likely.
   - Use family-local build helpers instead of fat binaries.
3. Prefer script-backed diagnostics.
   - `nsys` for timeline, overlap, pipeline, topology, launch trains.
   - `ncu` for one representative hot kernel.
   - `compute-sanitizer` before `cuda-gdb` for memory, race, sync, init.
   - Filter dumps before reading them.
4. PTX stays request-only.
   - Do not route into PTX unless explicitly asked.
   - Isolate the hot path first.
   - Dump only the relevant symbol or micro-primitive.

## Scripts

Prefer scripts over raw artifact reading.

### Shared

- `scripts/common/recommend_cuda_route.py` maps benchmark or profiler summaries
  to one narrow next route and reference path.
- `scripts/common/emit_arch_build_matrix.py` emits narrow `nvcc` gencode flags.
- `scripts/common/check_single_kernel_tu.py` checks whether a TU is safe for
  low-level inspection or needs splitting.
- `scripts/common/filter_objdump_sections.py` keeps only the relevant symbol and
  memory or branch lines from objdump-style dumps.
- `scripts/common/summarize_cuda_diagnostics.py` merges compact profiler,
  benchmark, debugger, and dump summaries into one short report.

### Profiling

- `scripts/profile_nsys.sh`
- `scripts/profile_ncu.sh`
- `scripts/combine_benchmark_summaries.py`

### Crash

- `scripts/debug_crash.sh`
- `scripts/debug_compute_sanitizer.sh`
- `scripts/debug_cuda_gdb.sh`

### Low-Level

- `scripts/dump_ptx_hotspot.sh`
- `scripts/split_cuda_translation_unit.py`

### Build

- `scripts/architectures/volta/emit_gencode.py`
- `scripts/architectures/volta/emit_profile_build.py`
- `scripts/architectures/volta/summarize_ptxas_verbose.py`
- `scripts/architectures/volta/summarize_sass_hotspot.py`
- `scripts/architectures/volta/gen_native_bench_matrix.py`
- `scripts/architectures/ampere/emit_gencode.py`
- `scripts/architectures/hopper/emit_gencode.py`
- `scripts/architectures/blackwell/emit_gencode.py`
- `scripts/systems/native/emit_native_build_flags.py`
- `scripts/systems/gb200-nvl72/emit_gb200_build_flags.py`

## Output Requirements

Be explicit about:

- which system route was chosen and why
- which architecture family was chosen and why
- which micro-router was chosen and why
- whether the workload is Tensor Core-eligible and why
- whether the chosen route is Tensor Core-capable library-backed, Tensor
  Core-capable custom-kernel, or regular custom-kernel
- whether the workload is limited by PCIe, HBM traffic, occupancy, register
  pressure, launch count, branch behavior, or communication topology
- whether the code is still CPU-centric and what decomposition change is needed
  before low-level tuning
- whether the binary should be architecture-specific for the current step
- whether the hot path is already isolated enough for PTX, SASS, or objdump work
- which memory tier should hold the critical intermediates
- whether fusion is required, optional, or now too expensive
- whether the answer came from compact summaries or required raw-artifact
  inspection
- which reference informed the recommendation

## Hard Constraints

- Do not let general multi-architecture guidance weaken the native Volta route.
- Do not treat H200 as a separate architecture route in this first pass.
- Do not recommend consumer-GPU doctrine when the user said datacenter cards.
- Do not inflate routing by loading broad manuals before a micro-router or
  script-backed summary has failed.
- Do not collapse everything into one fat binary when narrow builds would make
  tuning or debugging easier.
- Do not fall back to a regular FP kernel for dense or blocked math before
  checking whether a Tensor Core-capable path should own it.
- Do not treat all divergence as wrong; compare it against extra launches,
  memory traffic, and specialization cost.
- Do not use PTX to skip higher-level decomposition, layout, or fusion choices.
- Do not port CPU-centric code literally to CUDA when the real win requires a
  new boundary or layout.
