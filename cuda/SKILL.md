---
name: cuda
description: Primary CUDA skill for datacenter NVIDIA GPUs. Use for CUDA build, profiling, debugging, optimization, architecture and toolchain work, benchmarks, resource-aware execution, sparse/scientific workloads, Torch extensions, and CPU-to-CUDA porting across Volta, Ampere, Hopper, and Blackwell.
---

# CUDA

## Repository workflow

For substantial repository work, use the `project-control` Codex profile.
Invoke this skill only for the bounded CUDA operation and scope authorized by
Project Control, when the user explicitly requests CUDA maintenance, or while
Project Control itself is being debugged. MCP startup never imports GPU
libraries, starts a model, reserves a GPU, scans a repository, or runs a
benchmark.

The model owns the CUDA question: define the workload, success metric, important
operation or symbol, and concrete optimization hypothesis. It also decides
algorithm, representation, fusion, precision, specialization, library versus
custom ownership, source edits, and whether evidence blocks the next decision.

Use one high-level controller call:

```bash
python <skill-dir>/scripts/cuda_controller.py inspect --project <repo> --json
python <skill-dir>/scripts/cuda_controller.py run --spec <spec.json|-> --json
python <skill-dir>/scripts/cuda_controller.py background arm --spec <spec.json|-> --json
python <skill-dir>/scripts/cuda_controller.py background enqueue --spec <spec.json|-> --json
```

Arming is explicit and persistent. Once armed, relevant todo completion,
checkpoint, and handoff events wake private correctness/benchmark work without
polling or changing todo output. An explicit `run` is foreground work: it
preempts conflicting background activity and reserves its GPUs atomically.
Campaign state stays project-local; physical GPU, profiler, interference-domain,
and host-pressure interlocks are host-global.
Keep builds in `benchmark.build_argv`; they run without a GPU lease. Background
correctness repeats, fails fast, and skips only its dependent measurement chain,
so unrelated watches keep using available devices. Comparable benchmark and
profiler timing remains serialized through the host mutex.
Use `background backfill --spec ...` once for project-supplied historical
task/source-revision/benchmark mappings; it never rewrites todo history.
Read `references/controller-background-contract.md` only when authoring these
controller specs.

Retrieve only what the current decision needs:

```bash
python <skill-dir>/scripts/cuda_controller.py evidence <id> --focus <topic> --json
python <skill-dir>/scripts/cuda_controller.py guide --query "<architecture and question>" --json
```

Guidance returns exact bounded sections from the preserved Markdown corpus.
Evidence summaries point to authoritative raw artifacts. Generated context views
are read-only; edit canonical source only. The controller uses
cpp-context-compiler for small semantic source slices and falls back to
`split_cuda_translation_unit.py` when semantic retrieval is unavailable.
For accepted changes, prefer a performance-intent ctxpp task packet carrying
changed paths plus task and campaign identity before the slice/TU fallback.

Healthy background results remain silent. Correctness failures, material
regressions, missed targets, serious variance/contamination, and relevant
bottlenecks are ranked and bounded. The model interprets conflicting evidence
and decides promotion.

PTX/SASS remains explicit-request-only. Existing scripts, architecture labels,
routes, `ok`/`partial`/`rerun`, benchmark contracts, debug capture behavior,
and legacy mutex remain direct compatibility fallbacks. The complete prior
router and all substantive guidance remain available in
`references/legacy-skill-router.md` and the existing reference tree.
