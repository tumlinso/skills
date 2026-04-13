# Active Objectives

## Summary
Use this file as the canonical index for substantial multi-step work.

## Shared Assumptions
- Substantial cuda-v100 documentation work should be tracked in todos.md and a workstream file.
- New substantial skill work should add a dedicated workstream ledger and close it only after validation.
- New standalone skills should be tracked in todos.md and a dedicated workstream until validated.

## Suggested Skills
- `cuda-v100`
- `cuda-v100` - Primary specialization for V100 routing and references.
- `cuda-v100` - Primary skill being extended.
- `openacc-porting` - Review-first OpenACC assessment and incremental implementation skill.
- `compare-benchmarks` - Benchmark-contract model for summary-first follow-on validation.
- `todo-orchestrator` - Track the work in todos.md and a workstream ledger.
- `todo-orchestrator` - Track the multi-step skill creation and validation in the ledger.
- `cuda-v100` - Reference existing benchmark-summary and profiler-wrapper patterns without creating a dependency.
- `compare-benchmarks` - Standalone comparison harness skill for pitting implementation A against B under one contract.
- `todo-orchestrator` - Primary skill being extended and validated.
- `skill-creator` - Keep the skill concise while adding the new workflow surface.

## Useful Reference Files
- `cuda-v100/references/benchmark-standardization.md`
- `cuda-v100/references/benchmark-target-authoring.md`
- `compare-benchmarks/references/comparison-contract.md` - Shared benchmark contract to reuse for OpenACC follow-on guidance.
- `compare-benchmarks/references/profiler-workflow.md` - Summary-first profiler workflow to reuse in validation guidance.
- `todo-orchestrator/references/planning-workflow.md` - Planning and ledger workflow for multi-step repo changes.
- `cuda-v100/references/addendum-nvhpc-cpp.md` - Existing nearby route for offload tradeoffs.
- `cuda-v100/references/v100_programming_guide.md` - General V100 routing and optimization doctrine.
- `cuda-v100/references/v100_bioinformatics_guide.md` - Sparse bioinformatics examples and layout decisions.
- `cuda-v100/references/v100_cuda_cpp_optimize.md` - Low-level CUDA/C++ implementation guidance that should remain downstream of porting decisions.
- `cuda-v100/references/benchmark-standardization.md` - Existing summary-first benchmark contract pattern.
- `cuda-v100/references/benchmark-target-authoring.md` - Reference for interoperable benchmark wrapper contracts.
- `cuda-v100/scripts/with_benchmark_mutex.sh` - Existing mutex behavior to mirror in the new skill.
- `compare-benchmarks/references/comparison-contract.md` - Shared A/B run contract and summary layout.
- `todo-orchestrator/references/todo-format.md` - Canonical ledger and pickup-register layout.
- `todo-orchestrator/references/status-and-cleanup.md` - Claiming rules and explicit cleanup policy.

## Workstreams
- `cuda-v100-cpu-porting` | status: done | owner: unassigned | file: `todos/cuda-v100-cpu-porting.md` | objective: cuda v100 cpu porting
- `openacc-porting` | status: done | owner: unassigned | file: `todos/openacc-porting.md` | objective: create a standalone openacc-porting skill
- `compare-benchmarks-skill` | status: done | owner: unassigned | file: `todos/compare-benchmarks-skill.md` | objective: compare benchmarks skill
- `v100-model-design-low-level-ml` | status: done | owner: unassigned | file: `todos/v100-model-design-low-level-ml.md` | objective: add low-level ML boundary design guidance to v100-model-design
- `cuda-v100-crash-debugging` | status: done | owner: unassigned | file: `todos/cuda-v100-crash-debugging.md` | objective: add summary-first crash and debugger helpers to cuda-v100
- `todo-orchestrator-status-cleanup` | status: done | owner: codex | file: `todos/todo-orchestrator-status-cleanup.md` | objective: extend todo-orchestrator with todo-status pickup coordination and explicit cleanup
- `native-debugging` | status: done | owner: codex | file: `todos/native-debugging.md` | objective: create a standalone native-debugging skill for Linux C/C++ debugging with CUDA follow-on routing

## Global Blockers
_None recorded yet._

## Progress Notes
- Bootstrapped the `todo-orchestrator` workflow ledger for this repo.
- Started the `cuda-v100` benchmark mutex workstream and scoped the integration to shared script plumbing plus benchmark authoring docs.
- Added `scripts/with_benchmark_mutex.sh`, routed both profiler wrappers through it, and verified syntax plus a live contention test with a temporary lock file.
- Started the cuda-v100 CPU-porting documentation workstream.
- Initialized the cuda-v100-cpu-porting workstream and recorded the intended structure.
- Added `addendum-cpu-porting`, `cpu-porting-decision-tree`, `cpu-to-cuda-rewrite-patterns`, and `cpu-porting-sparse-bio`.
- Updated `SKILL.md`, NVHPC routing, general V100 routing, CUDA/C++ optimize guidance, bio guidance, and OpenAI metadata to expose the new CPU-porting path.
- Validated the updated skill with `quick_validate.py`.
- Initialized the `openacc-porting` skill with `skill-creator`, then replaced the template with a two-mode review and implementation workflow.
- Added a focused OpenACC reference set, two helper scripts, tests, and AGENTS routing that reuse benchmark discipline from `compare-benchmarks` without duplicating its harness role.
- Validated `openacc-porting` with unit tests plus `quick_validate.py`.
- Initialized the compare-benchmarks workstream and captured the intended standalone script-heavy design.
- Replaced the scaffold with a standalone compare-benchmarks skill, UI metadata, and routing docs.
- Added a script-heavy comparison suite: mutex wrapper, harness init, CLI/Python wrapper generators, compare runner, summary combiner, profiler wrappers, and component diff.
- Validated the skill with quick_validate.py, compiled all Python scripts, and smoke-tested the summary pipeline on mocked implementation outputs.
- Created the compare-benchmarks standalone skill with its own mutex, summary, and profiler-orchestration scripts.
- Started the `v100-model-design` low-level-ML boundary workstream for framework-free forward/backward/optimizer design guidance.
- Added a new `v100-model-design` route for low-level ML subsystem design with references for manual gradients, optimizer ownership, trainer-loop design, and sparse layout-driven framework bypass.
- Updated the existing custom-op, model-family, bioinformatics, registry, and metadata docs to distinguish ordinary extensions from low-level ML subsystem ownership.
- Validated the skill with repo-local checks: YAML parsing, front-matter parsing, description-length check, and reference existence validation.
- Started the `cuda-v100` crash-debugging workstream for summary-first segfault and CUDA hard-failure triage.
- Added a dedicated `cuda-v100` crash-debugging route, a compact crash reference set, and helper scripts for first-pass crash capture, `compute-sanitizer`, batch `cuda-gdb`, and combined summaries.
- Validated the new crash workflow with `quick_validate.py`, shell and Python syntax checks, a synthetic host segfault smoke test, a real CUDA illegal-access `compute-sanitizer` smoke test, and a batch `cuda-gdb` backtrace smoke test.
- Implemented additive pickup tracking, cleanup helpers, and quick-start requirements for exact required skills and references.
- Validated the extension with the todo-orchestrator unit tests, script compilation, and frontmatter/UI metadata checks.
- Started the `native-debugging` workstream for a standalone Linux-first C/C++ debugging skill that reuses the summary-first crash-debugging pattern and routes CUDA-specific debugging to `cuda-v100`.
- Created the standalone `native-debugging` skill with router docs, native debug references, summary-first helper scripts, and Ubuntu install guidance.
- Validated `native-debugging` with `quick_validate.py`, shell and Python syntax checks, a segfault capture smoke test, an ASan smoke test, an unsandboxed `gdb` backtrace smoke test, an unsandboxed `strace` missing-path smoke test, a `perf stat` smoke test, and a combined-summary smoke test.
- Hardened `update_todos.py` with a JSON `--payload-file` path so ledger updates can preserve backticks, globs, and markdown-heavy repro text without shell expansion.
- Clarified the serial execution rules so unclaimed `ready` or `idle` workstreams must be picked up immediately instead of waiting or asking the user what to do next.

## Next Actions
- Create or resume a new workstream ledger when the next substantial repo task arrives.
- No immediate action; resume only if the user wants deeper CPU-porting examples or additional scripts.
- No immediate action; extend the profiler wrappers only if a repo needs deeper compare-specific integration.
- No immediate action; resume the `v100-model-design` route only if the user wants deeper examples or a parallel implementation-side handoff in `cuda-v100`.
- No immediate action; extend the `cuda-v100` crash route only if the user wants Torch-extension-specific wrappers or deeper debugger automation.
- Run skill-level validation and sync the repo ledgers to the new format.
- Implementation is complete; call `todo-cleanup` only if explicit cleanup is requested.
- No immediate action; extend `native-debugging` only if the user wants additional wrappers or deeper symbolization helpers.
- Resume only if more todo-orchestrator script hardening is needed.
- Resume only if more todo-orchestrator execution wording needs tightening.

## Done Criteria
- Every active workstream in `todos/` is reflected here with a current status.
- The `cuda-v100` benchmark path serializes measurement runs through a shared mutex and the skill docs say how to use it for raw benchmark commands.
- cuda-v100 can route explicit CPU-centric porting questions into a dedicated set of references.
- The new docs distinguish offload from native CUDA and prioritize algorithmic rewrite first.
- The sparse bio route explains how to port irregular CPU-centric scientific code without copying the CPU decomposition literally.
- `openacc-porting` exists as one standalone skill with review and implementation modes.
- The new skill emits a concrete `openacc-review.md` artifact, teaches data-region planning, and preserves correctness-before-tuning.
- Benchmark follow-on guidance borrows the shared-contract and summary-first approach from `compare-benchmarks` without turning the skill into a generic benchmark tool.
- The new skill can scaffold or normalize implementation A/B wrappers under one benchmark contract.
- The skill owns its own mutex and summary-first profiler workflow.
- The skill stays separate from cuda-v100 while allowing optional CUDA-specific follow-on.
- The skill exists as a standalone compare-benchmarks skill under .agents/skills.
- It can scaffold or normalize implementation A/B wrappers and produce compact comparison summaries.
- It owns its own mutex and summary-first profiler workflow without depending on cuda-v100.
- `v100-model-design` can route low-level ML subsystem questions into explicit design docs for forward/backward ownership, optimizer ownership, trainer-loop boundaries, and sparse layout-driven framework bypass.
- `cuda-v100` can route crash and debugger questions into compact crash summaries, sanitizer helpers, and batch `cuda-gdb` escalation without forcing raw debugger output into context.
- todo-orchestrator tracks pickup-ready versus claimed work without replacing the existing workstream status model.
- todo-cleanup stays explicit and only succeeds when every tracked workstream is done.
- `native-debugging` exists as a standalone skill with Linux-first native crash, sanitizer, tracing, symbolization, and CPU profiling routes plus explicit CUDA follow-on references.
