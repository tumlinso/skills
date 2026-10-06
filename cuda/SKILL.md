---
name: cuda
description: CUDA programming, porting, correctness, profiling, and optimization on datacenter NVIDIA GPUs. Covers Volta, Ampere, Hopper, Blackwell, sparse/scientific workloads, Torch extensions, and topology-aware execution with host GPU interlocks.
---

# CUDA

Use the workload, target GPU, numerical contract, and evidence to choose the
next reference. **The agent is the semantic router.** Read one focused guide
for the current decision; open its deeper material only when needed. Paths
below are relative to this skill. Use `rg --files` and `rg -n` for discovery
or to locate a heading in a long manual.

## Working method

1. Define the operation, representative shapes/data, layouts, dtypes, numerical
   tolerances, and success metric. Record the equation, state transition, and
   scientific invariants; keep an independent correctness oracle. Separate
   resident kernel time from transfers, setup, and end-to-end time.
2. Choose the semantic unit, then consider encodings, layouts, and ownership
   that make its required operations native to the machine. For meaningful
   structure or reuse, use [machine-aligned design](references/common/machine-aligned-design.md)
   to generate and reject candidates against a complete cost model. Keep routine
   library-shaped work on its library route. Check library
   and Tensor Core eligibility for dense/blocked work; account for packing and
   precision costs. For irregular work, choose layout and thread/warp ownership.
   Fusion must save launches or traffic without losing the gain to spills,
   synchronization, or expensive divergence. Graphs do not remove HBM passes.
3. Establish correct, representative behavior. Read compact evidence before
   raw artifacts. Use Nsight Systems for timeline/overlap/launch/communication
   questions, then Nsight Compute for an identified hot kernel. Use sanitizers
   for memory, race, initialization, or synchronization failures.
4. Change a lever justified by the limiter; compare the same workload and
   measurement protocol. Keep builds narrow to the target architecture during
   tuning. Report correctness, end-to-end effect, evidence limits, and the next
   unresolved decision. Profiler replay timings are not throughput results.

## Choose the current decision

| Question | Focused reference |
| --- | --- |
| Library, kernel building blocks, or custom CUDA? | [Compute libraries](references/common/compute-libraries.md) |
| Semantic operator has a meaningful representation or ownership choice? | [Machine-aligned design](references/common/machine-aligned-design.md) |
| Fuse, split, specialize, branch, or change memory tier? | [Kernel mechanics](references/common/kernel-mechanics.md) |
| CPU algorithm needs GPU decomposition/layout | [CPU porting](references/workloads/cpu-porting.md) |
| Sparse scientific/omics formats and ownership | [Sparse workloads](references/workloads/sparse-bio.md) |
| Hot kernel, roofline, registers, stalls | [Hot-kernel tuning](references/profiling/hot-kernel.md) |
| Measurement setup or benchmark contract | [Diagnostics](references/profiling/diagnostics-workflow.md), [benchmarks](references/profiling/benchmark-standardization.md) |
| Crash, illegal access, race, sync, device assert | [Crash debugging](references/debugging/crash-debugging.md) |
| Allocation budget or workload does not fit | [Memory budgeting](references/systems/memory-budgeting.md) |
| Host-device transfers or GPU starvation | [Host-device pipeline](references/systems/host-device-pipeline.md) |
| Multi-GPU placement, NCCL, DDP | [Topology and DDP](references/systems/ddp-topology.md) |
| PyTorch C++/CUDA op, stream/binding/autograd boundary | [Torch extensions](references/specialized/torch-extensions.md) |
| NVHPC, OpenACC, OpenMP target, stdpar | [NVHPC choices](references/specialized/nvhpc.md) |
| Explicit PTX/SASS request after isolating a hot path | [Low-level inspection](references/low-level/ptx.md) |

## Apply the relevant architecture or system

Read the matching family overlay when its constraints affect the decision;
do not load other families. Shared guides identify their Volta-specific rules.

| Target | Architecture guidance |
| --- | --- |
| V100 / Volta / `sm_70` | [Volta](references/architectures/volta/router.md); [Tensor Core decisions](references/architectures/volta/tensor-cores.md) for dense/blocked math |
| A100 / Ampere / `sm_80` | [Ampere](references/architectures/ampere/router.md) |
| H100/H200 / Hopper / `sm_90` | [Hopper](references/architectures/hopper/router.md) |
| B100/B200 / Blackwell | [Blackwell](references/architectures/blackwell/router.md) |

For this host, read [native system constraints](references/systems/native.md).
For Grace-Blackwell deployment, read [GB200 NVL72](references/systems/gb200-nvl72.md).
Discover current topology and device identity; recorded physical indices are
examples, not placement authority.

## Execute on the shared host

For substantial repository work, use Project Control's task scope and lifecycle.
This skill supports bounded CUDA work authorized there, explicitly requested
CUDA maintenance, or Project Control debugging.

Before running GPU work, read [host execution](references/execution/host-execution.md).
Use `scripts/cuda_controller.py run --spec <spec.json|-> --json` for foreground
execution. It owns reservations, foreground preemption, quiescence, profiler
and timing interlocks. Device visibility or the benchmark mutex alone does not
replace it. Background campaigns require explicit persistent arming; their
specification is in the linked execution reference.

Keep evidence transforms, build helpers, and source-context compilation in
`scripts/`. Use their compact outputs to inform judgment. PTX/SASS stays
explicit-request-only; isolate the relevant symbol before dumping. For source
layout and dump preparation, read [code organization](references/common/code-organization.md).
