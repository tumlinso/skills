# Volta Router

Assume **Tesla V100 16 GB, `sm_70`**, usually on the native 4xV100 host. Use
this route for V100-specific tuning, native Volta behavior, or `sm_70`
implementation questions. Keep builds narrow to `sm_70`, prefer native
measurements over generic CUDA medians, and treat repeated HBM passes as a
first-class loss.

The recorded native-host profile has fast pairs `0 <-> 2` and `1 <-> 3`, with
`0 <-> 3` and `1 <-> 2` the worst steady-state paths. Revalidate runtime
topology before applying rank placement; controller admission and interlock
rules govern GPU use. Read benchmark and profiler summaries before raw reports,
then follow the authored route table below.

## Architecture-specific routes

| Problem | Route and decision cue |
| --- | --- |
| Mixed native path, bottleneck not yet classified | [Native V100 guide](native-v100-extreme.md). If loss is repeated HBM traffic or launch trains, continue to [fusion and specialization](fusion-and-specialization.md); if one kernel dominates, use [hot-kernel profiling](../../profiling/hot-kernel.md); if dense blocked math fits, check [Tensor Core routing](tensor-cores.md). Load the deep guide only after classification remains mixed. |
| Fuse, split, specialize, bin, or use graphs | [Fusion and specialization](fusion-and-specialization.md). Bias toward fusion when splitting rereads or rewrites full tensors through HBM; moderate divergence can be cheaper than launch trains and extra passes. Split for spills, occupancy collapse, or stable workload classes. Use CUDA Graphs after obvious fusion and grouping opportunities. Consult [common kernel mechanics](../../common/kernel-mechanics.md) or [launch-bound patterns](../../profiling/roofline-launch-bound-patterns.md) only if the tradeoff remains unclear. |
| One hot kernel, `ncu` limiter, spills, or occupancy | Classify with [hot-kernel profiling](../../profiling/hot-kernel.md) first. If memory-bound, fix bytes or fusion depth before instruction tuning; if compute-path mismatch, switch to [Tensor Core routing](tensor-cores.md); for register/shared-memory limits, use [register pressure and occupancy](register-pressure-and-occupancy.md), then [V100 optimization mechanics](optimization-guide.md) for the specific lever. |
| Tensor Core eligibility or weak Tensor Core activity | Start with [Tensor Core routing](tensor-cores.md): check eligibility before owning a regular FP kernel and keep a clean library path if it expresses the op. For custom-op fusion/layout ownership, consider CUTLASS or WMMA; load [low-level Tensor Core mechanics](tensor-core-low-level.md) only when that path is already correct but still too slow or glue-heavy. |
| PyTorch C++/CUDA extension | Keep Python thin and the real boundary in C++/CUDA. Check Tensor Core ownership for dense math, reconsider the op boundary when it is only repeated library launches, and switch to [crash triage](../../debugging/crash-debugging.md) when it fails. Continue with [extension guidance](../../specialized/torch-extensions.md) and its [build and binding playbook](../../specialized/torch-extension-playbook.md); return here for Tensor Core or HBM-heavy fusion choices. |
| Benchmark design and evidence | Keep outputs structured and read `summary.txt` or `combined_summary.txt` before raw artifacts. Use [native benchmark loop](native-benchmark-loop.md), then [benchmark standardization](../../profiling/benchmark-standardization.md) for contract or summary shape; use [Volta profiling interpretation](profiling-interpretation.md) if measurement validity remains weak. |

## Shared problem classes

For system-level dense-library choices, Tensor Core shape engineering,
communication strategy, and the V100 priority order, open the
[Volta programming guide](programming-guide.md) when that broad decision is
needed; keep it closed for routine kernel triage.

Use the skill's shared guides for [memory fit](../../systems/memory-budgeting.md),
[host-device pipeline](../../systems/host-device-pipeline.md),
[DDP topology](../../systems/ddp-topology.md), [crash debugging](../../debugging/crash-debugging.md),
[CPU porting](../../workloads/cpu-porting.md), [PTX/SASS](../../low-level/ptx.md),
[NVHPC](../../specialized/nvhpc.md), and [sparse bioinformatics](../../workloads/sparse-bio.md).
Only when PTX/SASS work is explicitly requested, and after the hot symbol is
isolated, use [Volta PTX guidance](ptx-extreme.md) or [SASS/PTX triage](sass-and-ptx-triage.md).

## Reporting the route

State whether the route assumed native `sm_70`, which evidence drove the call
(benchmark, Nsight Systems, Nsight Compute, or a focused dump), and which owner
remains appropriate: library, fused custom CUDA, CUTLASS, WMMA, or another
implementation. Name the first dominant loss among HBM traffic, launch trains,
register pressure, Tensor Core routing, and topology.
