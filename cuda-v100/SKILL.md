---
name: cuda-v100
description: Entry point for Tesla V100 16GB CUDA work on native Volta `sm_70`, especially 4-GPU hosts with diagonal NVLink pairs. Use for profiling, fitting, scaling, and optimizing CUDA/C++ workloads, including Tensor Core routing, low-level kernels, request-only PTX guidance, fusion and divergence tradeoffs, memory budgeting, DDP/NCCL topology, host-device pipeline bottlenecks, large-data benchmark saturation, sparse bioinformatics pipelines, Torch extensions, and counter-driven tuning toward practical V100 limits.
---

# CUDA V100

Use this as the public entry point for the V100 skill family.

Do not scan every reference. Choose one path, load that file first, and return here only when the bottleneck changes.

If the user is asking what model family or architecture to build, use `v100-model-design` first, then return here for memory fit, topology, custom-op, and Volta-specific implementation work.

For benchmark work, prefer summary-first workflows. Read compact benchmark or profiler summaries first, then inspect raw logs, CSVs, or reports only if the summaries disagree or remain inconclusive.

Target **Tesla V100 16GB (`sm_70`)** systems, especially this 4-GPU topology:

- fast NVLink pair: `GPU0 <-> GPU2`
- fast NVLink pair: `GPU1 <-> GPU3`
- acceptable leader exchange: `GPU0 <-> GPU1` and `GPU2 <-> GPU3`
- worst steady-state paths: `GPU0 <-> GPU3` and `GPU1 <-> GPU2`

## Ground Rules

1. Choose the highest-throughput path for **Volta**.
   - Use cuBLAS, cuBLASLt, cuDNN, cuTENSOR, cuSPARSE, NCCL, CUTLASS, or TensorRT when the workload maps cleanly to them.
   - Prefer custom CUDA early when the workload is glue-heavy, irregular, sparse, or multi-pass and fusion can remove HBM traffic or launch overhead.
   - Reformulate shapes, layouts, or boundaries when that unlocks a faster Volta path.

2. Treat **PCIe 3.0 as the default enemy**.
   - Keep data resident on GPU.
   - Keep high-traffic work within the real NVLink pairs.
   - Make cross-pair communication coarse-grained and infrequent.

3. Optimize for **Volta**, not newer architectures.
   - Build for `sm_70`.
   - Stay on a CUDA 12.x toolchain for native Volta work.
   - Do not assume TF32, `cp.async`, or BF16 Tensor Core fast paths.

4. Measure before arguing.
   - Use Nsight Systems for timeline and overlap questions.
   - Use Nsight Compute for hot-kernel questions.
   - Compare against the fastest plausible alternative, not just the current implementation.

## Choose Your Path

Choose the first statement that is true. Load only the file named in that row first.

| If the task sounds like... | Start here | Then load only if needed |
| --- | --- | --- |
| "It does not fit in 16 GB", "batch size collapsed", "buffers exploded" | `references/addendum-memory-budgeting.md` | `references/v100_programming_guide.md` after the fit plan is stable |
| "DDP/NCCL is slow", "which ranks go where", "multi-GPU scaling is bad" | `references/addendum-ddp-topology.md` | `references/v100_programming_guide.md` for wider decomposition choices |
| "GPU is idle", "HtoD copies dominate", "input pipeline is starving the device" | `references/addendum-host-device-pipeline.md` | `references/v100_profiling_interpretation.md` if the measurement setup is weak |
| "Should these kernels be fused?", "is divergence actually bad here?", "should I split this into specialized kernels?", "which CUDA memory tier should hold this data?", "is launch overhead worse than divergence?" | `references/addendum-kernel-mechanics.md` | `references/v100_cuda_cpp_optimize.md` and `references/roofline-launch-bound-patterns.md` |
| "One kernel is hot", "Nsight Compute shows a limiter", "should this stay custom?" | `references/addendum-kernel-roofline-lab.md` | `references/v100_cuda_cpp_optimize.md` for implementation details |
| "Why are Tensor Cores not firing?", "how do I force the Volta Tensor Core path?", "this dense or blocked workflow is not drawing enough power", "should I reformulate this for Tensor Cores?" | `references/addendum-tensor-core-routing.md` | `references/volta-tensor-core-low-level.md` only when cuBLAS, cuBLASLt, or CUTLASS leave a stable gap |
| "I explicitly want PTX guidance", "when should I use inline PTX here?", "teach me PTX optimization for this kernel", "show PTX choices for sparse hot paths", "I want lower-level branch-avoidance options" | `references/addendum-ptx-routing.md` | `references/ptx-volta-extreme.md` and `references/ptx-sparse-bio-hotpaths.md`, but only when PTX was explicitly requested |
| "Should this use NVHPC, OpenACC, OpenMP target, or stdpar?" | `references/addendum-nvhpc-cpp.md` | `references/v100_cuda_cpp_optimize.md` once the abstraction choice is locked |
| "Write or fix a PyTorch C++/CUDA op", "where should the extension boundary sit?" | `references/addendum-torch-extensions.md` | `references/addendum-kernel-roofline-lab.md` only after the op already works |
| "This is sparse omics / bio data", "which layout or phase boundary is right?" | `references/addendum-bio-data-layouts.md` | `references/v100_bioinformatics_guide.md` for the broader sparse pipeline |
| "Standardize benchmarks", "make benchmark summaries concise", "add large plus real data tiers", "add compute- and transfer-saturating large cases", "write benchmark targets that interoperate with the skill" | `references/benchmark-standardization.md` | `references/benchmark-large-data.md`, `references/benchmark-target-authoring.md`, and `references/benchmark-real-data.md` |
| "I need a general V100 CUDA/C++ implementation or optimization path" | `references/v100_programming_guide.md` | one base manual below, then one addendum only if a dominant bottleneck appears |

## Opening Moves

After choosing a path, do only the opening move for that path before loading more references.

### Path: Memory

1. Build the memory budget.
2. Identify the dominant category.
3. Choose the least destructive fit strategy.
4. Return here when the job fits and the next bottleneck is clear.

### Path: DDP / NCCL

1. Confirm the real fast pairs are `0 <-> 2` and `1 <-> 3`.
2. Pick a rank layout that keeps steady-state traffic pair-local.
3. Run only the minimal NCCL experiments needed to validate the layout.
4. Return here when topology is no longer the main uncertainty.

### Path: Host / Device Pipeline

1. Prove the device is being starved with Nsight Systems or an equivalent timeline.
2. Classify the stall: loader, collation, pinned-memory, copy fragmentation, or NUMA placement.
3. Repair batching and overlap before touching kernels.
4. Return here when the device-side hot path becomes the limiter.

### Path: Kernel Mechanics

1. Read `references/addendum-kernel-mechanics.md`.
2. Decide whether the real loss comes from memory passes, launch count, divergence, or over-fusion.
3. Choose between fusion, specialization, binning, or memory-tier relocation before micro-tuning.
4. Return here once the kernel structure is basically right and the remaining work is profiler-driven tuning.

### Path: Roofline / Hot Kernel

1. Confirm the benchmark window is representative.
2. Classify the limiter before editing code.
3. Change only the lever that matches the limiter.
4. Return here if the correct fix is broader than one kernel.

### Path: Tensor Core Routing

1. Read `references/addendum-tensor-core-routing.md`.
2. Decide whether the workload is genuinely eligible for Tensor Core pursuit or whether bytes moved still dominate.
3. Fix dtype, blocking, padding, grouping, and library path selection before hand-tuning a custom kernel.
4. Route to `references/volta-tensor-core-low-level.md` only if the library-backed path is already sound and still leaves a stable gap.

### Path: PTX

1. Read `references/addendum-ptx-routing.md`, but only when PTX guidance was explicitly requested.
2. Decide whether the problem is really PTX-sized or whether algorithm shape, binning, fusion, or library choice still dominates.
3. Stay in `references/ptx-general-guidelines.md` for portable PTX guidance unless the user explicitly wants the deepest Volta-specific path.
4. Route to `references/ptx-volta-extreme.md` or `references/ptx-sparse-bio-hotpaths.md` only after the hotspot and the motivation for PTX are both clear.

### Path: NVHPC

1. Decide whether the abstraction can express the hot path without hidden data motion.
2. Keep explicit CUDA or libraries for the performance-critical region if needed.
3. Return here once the surface choice is stable.

### Path: Torch Extension

1. Define the op boundary before writing kernels.
2. Keep Python thin and C++ explicit.
3. Create or update `<repo_root>/custom_torch_ops.md` for nontrivial ops.
4. Return here when the remaining work is ordinary Volta tuning.

### Path: Sparse Omics

1. Identify the biological phase and whether rows or features drive locality.
2. Choose the sparse format and the sparse-to-dense boundary.
3. Return here once the hot phase is clear enough to route into memory, pipeline, or kernel tuning.

### Path: Benchmark Standardization

1. Read `references/benchmark-standardization.md`.
2. Make the benchmark emit structured raw measurements and let the scripts emit the concise interpretation.
3. Add `small`, `large-compute`, `large-transfer`, and `real` runs before calling the benchmark representative.
4. Read `references/benchmark-large-data.md` when the question is how to actually saturate compute, transfers, or collectives on this host.
5. Read `references/benchmark-target-authoring.md` when defining new build targets or output contracts.

### Path: General V100 Work

1. Read `references/v100_programming_guide.md`.
2. Choose one base manual from the next section.
3. Route into one addendum only when a single bottleneck class dominates.

## Load These Base Manuals Only When Needed

- Read `references/v100_programming_guide.md` for the overall V100 strategy, Tensor Core shape engineering, multi-GPU decomposition on this exact topology, and communication choices.
- Read `references/v100_cuda_cpp_optimize.md` for CUDA/C++ implementation details, build flags, kernel rules, profiling commands, WMMA or CUTLASS patterns, and libtorch or ATen integration.
- Read `references/v100_bioinformatics_guide.md` for sparse biological matrices, storage-format decisions, row-binned kernels, sparse preprocessing, and row-sharded omics pipelines.
- Read `references/v100_profiling_interpretation.md` when the first problem is poor measurement hygiene, profiler choice, or ambiguous profiler output.
- Read `references/benchmark-standardization.md` when the task is benchmark contract design, benchmark-summary design, or script-driven benchmark interpretation.
- Read `references/benchmark-large-data.md` when the task is benchmark saturation, large-data shape selection, or compute-versus-transfer stress design.
- Read `references/addendum-ptx-routing.md` only when the user explicitly asks for PTX, inline PTX, or handwritten PTX-level optimization guidance.

## Support Map By Path

Load these only after the matching addendum tells you the problem really belongs there.

- `references/addendum-bio-data-layouts.md`
  - then `references/bio-data-phases.md`
  - then `references/bio-format-decision-tables.md`
- `references/addendum-memory-budgeting.md`
  - then `references/memory-accounting.md`
  - then `references/memory-fit-strategy.md`
  - then `references/memory-scenario-formulas.md`
- `references/addendum-ddp-topology.md`
  - then `references/ddp-topology-playbook.md`
  - then `references/ddp-rank-layouts.md`
  - then `references/ddp-hierarchy-patterns.md`
  - then `references/ddp-nccl-experiments.md`
  - then `references/ddp-benchmark-interpretation.md`
- `references/addendum-host-device-pipeline.md`
  - then `references/pipeline-bottlenecks.md`
  - then `references/pipeline-overlap-rules.md`
- `references/addendum-kernel-mechanics.md`
  - then `references/v100_cuda_cpp_optimize.md`
  - then `references/roofline-launch-bound-patterns.md`
  - then `references/roofline-counter-triage.md`
  - then `references/roofline-playbook.md`
- `references/addendum-kernel-roofline-lab.md`
  - then `references/roofline-playbook.md`
  - then `references/roofline-counter-triage.md`
  - then `references/roofline-launch-bound-patterns.md`
  - then `references/roofline-cutlass-vs-handwritten.md`
  - then `references/roofline-example-tuning-loops.md`
- `references/addendum-tensor-core-routing.md`
  - then `references/v100_programming_guide.md`
  - then `references/v100_cuda_cpp_optimize.md`
  - then `references/volta-tensor-core-low-level.md`
- `references/addendum-ptx-routing.md`
  - then `references/ptx-general-guidelines.md`
  - then `references/ptx-volta-extreme.md`
  - then `references/ptx-sparse-bio-hotpaths.md`
- `references/addendum-nvhpc-cpp.md`
  - then `references/nvhpc-tradeoffs.md`
  - then `references/nvhpc-offload-models.md`
  - then `references/nvhpc-data-movement-modes.md`
  - then `references/nvhpc-library-interop.md`
  - then `references/nvhpc-case-notes.md`
- `references/addendum-torch-extensions.md`
  - then `references/torch-extension-playbook.md`
  - then `references/custom-torch-ops-registry.md`
  - then `references/v100_cuda_cpp_optimize.md`
- `references/benchmark-standardization.md`
  - then `references/benchmark-large-data.md`
  - then `references/benchmark-target-authoring.md`
  - then `references/benchmark-real-data.md`

## Common Sequences

Use these when the problem genuinely moves from one bottleneck class to another.

- `references/addendum-bio-data-layouts.md` -> `references/addendum-memory-budgeting.md`: choose the biologically correct layout first, then make it fit.
- `references/addendum-memory-budgeting.md` -> `references/addendum-host-device-pipeline.md`: make the job fit first, then repair staging and overlap.
- `references/addendum-ddp-topology.md` -> `references/addendum-host-device-pipeline.md`: lock rank placement first, then repair loading and transfer behavior seen by those ranks.
- main workflow -> `references/addendum-kernel-mechanics.md`: use when fusion, divergence, specialization, or memory-tier placement is the first unresolved design choice.
- `references/addendum-kernel-mechanics.md` -> `references/addendum-kernel-roofline-lab.md`: choose the right kernel structure first, then do counter-driven hot-kernel tuning.
- main workflow -> `references/addendum-tensor-core-routing.md`: use when dense or blocked work should probably be on Tensor Cores but the current path is leaving throughput on the table.
- `references/addendum-tensor-core-routing.md` -> `references/volta-tensor-core-low-level.md`: only after the cuBLAS, cuBLASLt, or CUTLASS path is correct and still too slow.
- explicit PTX request -> `references/addendum-ptx-routing.md`: use only when the user explicitly asks for PTX, inline PTX, or handwritten PTX-level optimization.
- `references/addendum-ptx-routing.md` -> `references/ptx-volta-extreme.md`: use when the user wants the deepest Volta-specific PTX path for `sm_70`.
- `references/addendum-ptx-routing.md` -> `references/ptx-sparse-bio-hotpaths.md`: use when the explicit PTX request is about sparse, irregular, or bioinformatics-heavy hot paths.
- `references/addendum-bio-data-layouts.md` -> `references/addendum-kernel-mechanics.md`: choose the biologically correct sparse phase first, then decide whether skew or glue should be handled by fusion or specialization.
- `references/addendum-torch-extensions.md` -> `references/addendum-kernel-roofline-lab.md`: fix the extension boundary first, then micro-optimize the hot backend.
- `references/addendum-torch-extensions.md` -> `references/addendum-kernel-mechanics.md`: fix the extension boundary first, then decide whether the backend should be fused, split, or library-backed.
- `references/benchmark-standardization.md` -> `references/benchmark-large-data.md`: define the benchmark contract first, then make the large stress tiers actually saturate compute, transfers, or collectives on this host.
- `references/benchmark-standardization.md` -> `references/benchmark-target-authoring.md`: define the benchmark contract first, then write interoperable build targets.
- `references/benchmark-standardization.md` -> `references/benchmark-real-data.md`: define the summary contract first, then make `real` dataset runs representative.
- main workflow -> `references/addendum-kernel-roofline-lab.md`: only after a hot kernel is isolated and the larger design is already reasonable.
- `v100-model-design` -> `references/addendum-torch-extensions.md`: pick the right model first, then implement only the custom ops the model actually needs.

## Scripts By Situation

Prefer the bundled scripts over ad hoc commands when they fit the task.

- Use `scripts/summarize_benchmark_run.py` to turn `run_config.json` plus `results.json` into compact benchmark summaries.
- Use `scripts/combine_benchmark_summaries.py` to merge benchmark, Nsight Systems, and Nsight Compute summaries into one short interpretation.
- Use `scripts/profile_nsys.sh` when the question is system timeline, overlap, communication, or pipeline starvation.
- Use `scripts/profile_ncu.sh` when the question is one hot kernel and the run window is already representative.
- Use `scripts/analyze_nsys_stats.py` after `profile_nsys.sh` to summarize timeline stalls and overlap.
- Use `scripts/analyze_ncu_csv.py` after Nsight Compute CSV export to classify likely kernel limiters.
- Use `scripts/summarize_kernel_efficiency.py` when you need a quick throughput-versus-ceiling read for a kernel set.
- Use `scripts/gen_dense_shapes.py` to generate representative dense benchmark shapes.
- Use `scripts/gen_sparse_omics_data.py` and `scripts/inspect_sparse_matrix.py` to create and inspect sparse omics inputs.
- Use `scripts/estimate_v100_training_memory.py` when the first question is memory fit.
- Use `scripts/emit_rank_layout_env.py` when testing rank placement or pair-local layouts.
- Use `scripts/estimate_transfer_time.py` when comparing staging strategies or transfer batch sizes.
- Use `scripts/emit_nvhpc_build_flags.py` when the task explicitly targets NVHPC compilation.
- Use `scripts/open_nsys_ui.sh` or `scripts/open_ncu_ui.sh` only when interactive profiler inspection is worth the cost.

## Output Requirements

Be explicit about:

- whether the advice assumes `sm_70`
- which path was chosen and why
- whether the answer came from a compact benchmark or profiler summary, or required raw-artifact inspection
- whether the recommendation is library-backed or custom-kernel
- whether PTX was explicitly requested and whether PTX was actually the right surface
- whether the PTX guidance stayed portable or escalated into a Volta-specific path
- whether the workload is eligible for Tensor Core pursuit or should stay on a non-Tensor-Core path
- whether the Tensor Core route was library-backed, CUTLASS-backed, or low-level custom
- whether divergence is actually part of the bottleneck or merely present
- whether extra launches are preferable to the current divergent structure
- whether the workload is limited by PCIe, HBM traffic, occupancy, register pressure, launch overhead, or communication topology
- whether the benchmark scenario is `small`, `large-compute`, `large-transfer`, or `real`
- whether the benchmark is intended to saturate compute, transfers, collectives, or glue-heavy steady state
- which memory tier should hold the critical intermediates
- what reformulation, layout change, fusion step, or padding decision would most improve throughput
- which base reference or addendum informed the recommendation

## Hard Constraints

- Do not assume ordinally adjacent GPUs are the fast pair on this machine.
- Do not recommend CUDA 13-native Volta compilation paths.
- Do not cargo-cult NCCL environment variables; benchmark before locking them in.
- Do not treat all warp divergence as automatically wrong; judge it against launch overhead, memory traffic, and specialization cost.
- Do not force Tensor Core thinking onto sparse or irregular phases that are fundamentally memory-bound, but do push dense and reformulable blocked paths harder than a generic CUDA guide would.
- Do not route into PTX unless the user explicitly asked for PTX-level guidance.
- Do not use PTX as an excuse to skip algorithm, layout, binning, or fusion decisions that are still unresolved.
- Do not load multiple addendums unless the task has clearly moved from one bottleneck class to another.
