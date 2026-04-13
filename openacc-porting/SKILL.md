---
name: openacc-porting
description: Review-first OpenACC portability assessment and incremental implementation for CPU-centric C, C++, or Fortran code. Use when Codex needs to assess whether a library is a good OpenACC target, classify candidate loops or kernels, plan data-region boundaries and directive choices, generate a staged `openacc-review.md`, or port appropriate regions incrementally to OpenACC while preserving CPU behavior and validating correctness before tuning. Do not use for handwritten CUDA, generic benchmarking, OpenMP-only work, or unrelated CPU-only refactors.
---

# OpenACC Porting

## Overview

Use this skill to review CPU-centric code for OpenACC suitability and, when the review supports it, port the best regions incrementally.

Keep this as one skill with two internal modes:

- `review`
- `implement`

Do not load every reference. Choose the current mode first, then read only the references that match the current bottleneck.

## Mode Selection

Use `review` mode by default when the user asks to:

- assess whether code is a good OpenACC target
- review or inspect a library for OpenACC portability
- identify loops, kernels, blockers, or data regions for OpenACC
- plan an OpenACC port
- refactor code to be more OpenACC-friendly before offload

Use `implement` mode when:

- the user explicitly asks for OpenACC code changes
- an `openacc-review.md` artifact already exists and supports incremental offload
- the code and portability risks are already understood well enough that implementation can begin safely

If implementation reveals that a region is transfer-dominated, dependency-heavy, or structurally hostile to OpenACC, switch back to review and update the artifact instead of forcing directives.

## Review Workflow

1. Read `references/review-procedure.md`.
2. Inspect the code for candidate regions before proposing directives.
3. Classify each region as:
   - easy to port
   - possible with restructuring
   - poor OpenACC target
4. Read `references/data-region-planning.md` to map host and device ownership, data-region boundaries, and call-boundary transfer risks.
5. Read `references/directive-selection.md` only after a region survives the portability screen.
6. Read `references/common-blockers.md` when aliasing, hidden temporaries, allocator churn, scans, indirect indexing, gather/scatter, or loop dependencies are visible.
7. Write `openacc-review.md` with:
   - scope
   - candidate regions
   - classification
   - blockers
   - proposed data-region plan
   - likely directives and strategy
   - staged implementation plan
   - validation checklist
   - performance risks and reasons the port may underperform

## Implementation Workflow

1. Start from `openacc-review.md` or create one first.
2. Choose the smallest useful region from the `easy to port` set. Use `possible with restructuring` only when the restructuring is limited and justified.
3. Preserve CPU behavior and public APIs where practical.
4. Prefer widening and stabilizing data regions before micro-tuning directive clauses.
5. Add only the minimum restructuring needed to make the first offload correct and reviewable.
6. Validate after every phase. Read `references/validation-checklist.md`.
7. Update `openacc-review.md` when implementation changes the blocker analysis, data-region plan, or directive strategy.
8. Stop and reclassify when the selected region becomes transfer-dominated, overly branchy, or dependency-bound in practice.

## Classification Rules

Treat these as good first candidates:

- regular counted loops over stable arrays or spans
- reductions that map cleanly to OpenACC reduction clauses
- regions where data can stay resident across several calls or timesteps
- loop nests that can benefit from `collapse` without semantic risk

Treat these as restructuring candidates:

- indirect indexing that is still regular enough to reason about
- scans or prefix-style logic that need decomposition changes
- hidden temporaries, allocator churn, or ambiguous ownership that can be cleaned up locally
- CPU-cache-oriented loop shapes that need layout or ordering reconsideration

Treat these as poor targets unless the wider algorithm changes:

- pointer-heavy pointer chasing
- severe gather/scatter with opaque ownership
- tiny loops dominated by transfer overhead
- strong loop-carried dependencies
- code whose control flow or state mutation is too scattered to keep data resident sanely

## Benchmark Follow-On

Do not turn this into a generic benchmark skill.

After correctness is stable, read `references/benchmark-follow-on.md` to compare the CPU baseline and OpenACC version under one shared scenario contract. Borrow the benchmark discipline from `compare-benchmarks`:

- keep scenario inputs identical
- make correctness or equivalence explicit
- serialize benchmark-producing runs on shared hosts
- read compact summaries first
- inspect raw profiler artifacts only if the summaries disagree or remain inconclusive

If the real problem becomes building an A/B harness rather than reasoning about OpenACC, hand that work to `compare-benchmarks`.

## Reference Map

- `references/review-procedure.md`
  - first stop for portability assessment and staged review artifacts
- `references/data-region-planning.md`
  - host and device ownership, residency, and transfer-boundary planning
- `references/directive-selection.md`
  - when to consider `parallel loop`, `kernels`, `collapse`, `reduction`, and `async`
- `references/common-blockers.md`
  - aliasing, temporaries, allocations, dependencies, indirect access, and tiny-kernel traps
- `references/validation-checklist.md`
  - build, correctness, regression, and performance sanity checks after each phase
- `references/benchmark-follow-on.md`
  - comparison rules for CPU baseline versus OpenACC follow-on work
- `references/examples.md`
  - example requests and expected skill behavior

## Helper Scripts

Use the scripts only to structure the review artifact. They do not replace code inspection.

```bash
python openacc-porting/scripts/summarize_openacc_candidates.py --input candidates.json --format markdown
python openacc-porting/scripts/generate_openacc_review.py --scope "Sparse stencil update" --candidate-json summary.json --output openacc-review.md
```

Use `summarize_openacc_candidates.py` to turn candidate notes into a compact summary with classifications, blockers, and suggested directives.

Use `generate_openacc_review.py` to create or refresh `openacc-review.md` from the summarized candidates.

## Output Requirements

Be explicit about:

- whether the current mode is `review` or `implement`
- which regions are easy, restructuring candidates, or poor targets
- where data should stay resident and where call boundaries will force transfers
- which directive family is being considered and why
- which blockers must be resolved before offload
- how CPU behavior is being preserved
- what was validated already versus what still needs measurement
- whether benchmarking belongs here or should route into `compare-benchmarks`

## Hard No's

- Do not assume every hotspot should be offloaded.
- Do not jump straight into directives without reviewing portability.
- Do not rewrite the task into CUDA.
- Do not optimize blindly before correctness is stable.
- Do not produce giant invasive rewrites unless the user explicitly asks for them.
- Do not treat benchmark harness authoring as part of this skill.
