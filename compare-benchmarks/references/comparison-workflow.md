# Comparison Workflow

Use this reference first whenever the task is to compare two libraries or implementations.

## Core Rule

Do not compare implementations casually.

Both sides must share:

- the same scenario inputs
- the same warmup and repeat policy
- the same correctness or equivalence checks
- the same output contract

## Choose The Mode

### Mode 1: Existing Targets

Use this when:

- both implementations already have runnable benchmark binaries or CLIs
- they can be normalized with light wrapper logic

Next:

- read `references/comparison-contract.md`
- use `scripts/run_compare.py`

### Mode 2: Wrapper Scaffolding

Use this when:

- the repo lacks directly comparable entrypoints
- implementation A and B need normalization through thin wrappers

Next:

- read `references/wrapper-authoring.md`
- use `scripts/init_compare_harness.py`

### Mode 3: Profiler Follow-On

Use this when:

- timing deltas exist but the dominant cause is still unclear
- component labels are stable enough to compare

Next:

- read `references/profiler-workflow.md`

### Mode 4: CUDA Follow-On

Use this when:

- the comparison already shows a CUDA-side hotspot
- the next question is no longer “which implementation is slower?” but “why is this GPU path slower?”

Next:

- read `references/cuda-follow-on.md`

## Summary-First Rule

Always read:

1. `summary.txt`
2. `combined_summary.txt` if profiler outputs exist

Only inspect raw logs or raw profiler artifacts if the summaries disagree or remain inconclusive.
