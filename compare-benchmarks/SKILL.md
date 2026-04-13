---
name: compare-benchmarks
description: Standalone skill for comparative benchmarking between two implementations or libraries. Use when Codex should pit implementation A against implementation B under one shared benchmark contract, scaffold comparison wrappers, serialize benchmark runs with a mutex, collect concise benchmark and profiler summaries, and identify which components explain the performance delta. Keep this separate from `cuda-v100`; route there only after the comparison already shows a CUDA-specific hotspot worth deeper tuning.
---

# Compare Benchmarks

Use this skill to compare two implementations fairly under one benchmark and profiler contract.

This skill is script-heavy by design. Prefer its scripts over ad hoc shell loops whenever possible.

Keep `SKILL.md` small. Treat it as a router. Load only the workflow or reference that matches the current stage.

## Workflow

1. Classify the comparison surface.
   - two existing benchmark binaries or CLIs already exist
   - wrappers must be scaffolded
   - benchmark-only run is enough
   - profiler follow-on is needed
   - CUDA-specific diagnosis may be needed after comparison

2. Read `references/comparison-workflow.md`.
   - use it to choose the right comparison mode first

3. Read `references/comparison-contract.md`.
   - both implementations must run under the same scenario contract
   - benchmark-producing runs must be serialized through the skill mutex

4. If wrappers are needed, read `references/wrapper-authoring.md`.
   - use wrapper scripts to normalize implementation A and B behind the same scenario inputs and output contract

5. If timing differences are already visible, read `references/component-breakdown.md`.
   - keep per-phase or per-component labels stable enough to diff side A and side B

6. If profiling is needed, read `references/profiler-workflow.md`.
   - read concise summaries first
   - inspect raw profiler artifacts only if the summaries disagree or remain inconclusive

7. If correctness or result equivalence is in doubt, read `references/correctness-and-equivalence.md`.

8. Only route into `references/cuda-follow-on.md` when the comparison already shows a CUDA-specific hotspot that belongs in `cuda-v100`.

## Script Map

Prefer these scripts over ad hoc commands:

- `scripts/with_benchmark_mutex.sh`
  - serialize benchmark-producing runs on shared hosts
- `scripts/init_compare_harness.py`
  - create a comparison run directory and wrapper templates
- `scripts/init_cli_wrapper.py`
  - scaffold a CLI-based implementation wrapper
- `scripts/init_python_wrapper.py`
  - scaffold a Python-based implementation wrapper
- `scripts/run_compare.py`
  - run implementation A and B under one comparison contract
- `scripts/summarize_compare_run.py`
  - emit a compact A/B summary
- `scripts/combine_compare_summaries.py`
  - merge benchmark and profiler summaries into one short interpretation
- `scripts/profile_compare_nsys.sh`
  - collect timeline summaries for both sides
- `scripts/profile_compare_ncu.sh`
  - collect Nsight Compute summaries for both sides when CUDA is involved
- `scripts/diff_component_breakdown.py`
  - compare the dominant phase or component differences

## Output Requirements

Be explicit about:

- implementation A and implementation B
- the shared scenario contract and whether it was truly identical
- whether correctness or equivalence checks passed
- whether benchmark runs were serialized through the mutex
- whether the result is benchmark-only or benchmark-plus-profiler
- which phase or component explains the largest delta
- whether the next step belongs in this skill or should route into `cuda-v100`
