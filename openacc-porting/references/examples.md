# Examples

## Review Requests

- "Review this library for OpenACC portability."
  - start in `review`
  - inspect loop structure, ownership, and data-region boundaries
  - emit `openacc-review.md`

- "Assess whether this sparse update kernel is a good OpenACC target."
  - classify the kernel
  - identify blockers such as indirect indexing, gathers, or residency problems
  - say clearly if it is a poor target

- "Identify loops and data regions for OpenACC offload."
  - focus on candidate discovery and residency boundaries, not immediate code changes

## Implementation Requests

- "Port this CPU-centric library incrementally to OpenACC."
  - begin from the review artifact
  - choose the smallest useful region first
  - preserve CPU behavior
  - validate after each phase

- "Refactor this code to be more OpenACC-friendly."
  - restructure only what is needed to remove blockers
  - avoid broad rewrites unless the request explicitly demands them

## Benchmark Follow-On Requests

- "Compare the CPU baseline and OpenACC version."
  - use the shared scenario contract
  - keep correctness explicit
  - summarize before profiling

## Bad-Fit Requests

- "Write a handwritten CUDA kernel for this."
  - not this skill

- "Benchmark these two libraries fairly under one harness."
  - use `compare-benchmarks`

- "Do a generic CPU cleanup."
  - not this skill unless the cleanup is explicitly in service of OpenACC portability
