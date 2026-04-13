# Review Procedure

Use this reference first whenever the user wants an OpenACC assessment, review, inspection, or port plan.

## Opening Pass

1. Identify the dominant CPU-shaped regions, not just the hottest function names.
2. Separate regular loop nests from control-heavy glue code.
3. Look for data lifetime first:
   - what stays live across iterations or calls
   - what is read-only
   - what is updated in place
   - what crosses function boundaries repeatedly
4. Record blockers before suggesting directives.

## Candidate Classification

Use these three buckets only:

- `easy to port`
  - regular loops over stable storage
  - data can stay resident across useful work
  - reductions are explicit and local
- `possible with restructuring`
  - aliasing, temporaries, allocations, scans, or indirect access are present but locally fixable
  - loop order or layout is CPU-centric and needs adjustment
- `poor OpenACC target`
  - pointer chasing
  - strong loop-carried dependencies
  - tiny kernels dominated by transfers
  - opaque or scattered state mutation that defeats sensible data regions

Do not promote a poor target into a restructuring candidate merely because it is hot.

## What To Inspect Explicitly

- reductions
- scans and prefix operations
- indirect indexing
- gather/scatter
- loop-carried dependencies
- aliasing and ownership ambiguity
- hidden temporaries
- allocator churn
- function boundaries that force transfers
- CPU-cache-oriented loop ordering or layout assumptions
- opportunities for wider data regions
- places where `async` may help
- places where `async` would only complicate correctness

## Required Review Artifact

Write `openacc-review.md` with these sections:

- scope
- candidate regions
- classification
- blockers
- proposed data-region plan
- likely directives and strategy
- staged implementation plan
- validation checklist
- performance risks

Keep the staged plan small:

1. first easy region
2. next restructuring-backed region if justified
3. deferred or rejected poor targets

## Review Output Rules

- Say clearly when OpenACC is a bad fit.
- Prefer a narrow first offload over a broad speculative rewrite.
- Preserve the option to stop after review if the transfer economics are poor.
