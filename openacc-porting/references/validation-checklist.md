# Validation Checklist

Use this reference after every implementation phase and before making performance claims.

## Build Checks

- confirm the existing build still works for the CPU path
- add only the compiler flags and pragmas needed for the current phase
- keep warnings or diagnostics visible, especially around data movement and parallelization

## Correctness Checks

- compare against the CPU baseline on representative inputs
- confirm reductions still produce acceptable results
- test edge cases with small sizes, empty ranges, or awkward shapes
- verify that any async work still respects dependencies

## Regression Checks

- preserve public APIs where practical
- confirm unchanged code paths still behave the same
- avoid mixing unrelated refactors into the port

## Performance Sanity Checks

- measure only after correctness is stable
- compare CPU baseline and OpenACC under the same scenario inputs
- explain when the result is transfer-dominated instead of kernel-limited
- say explicitly when the offload is slower

## Summary-First Benchmark Rule

Borrow this from `compare-benchmarks`:

- keep one shared scenario contract
- state correctness or equivalence status explicitly
- serialize benchmark-producing runs on shared hosts
- read compact summaries first
- inspect raw profiler artifacts only when summaries remain inconclusive

If the real job becomes building an A/B comparison harness, use `compare-benchmarks` rather than expanding this skill.
