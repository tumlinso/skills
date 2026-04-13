# Benchmark Follow-On

Use this reference only after the OpenACC path is correct enough to compare against the CPU baseline.

This skill borrows benchmark discipline from `compare-benchmarks`. It does not replace that skill's harness or wrapper workflow.

## Shared Scenario Contract

Compare the CPU baseline and OpenACC version under one shared contract:

- same dataset or input class
- same warmup and repeat counts
- same steady-state window
- same correctness or equivalence rule
- same mutex path on shared hosts

Record the contract in the review artifact or benchmark notes before interpreting the numbers.

## Required Comparison Notes

Every benchmark follow-on should say:

- baseline name
- OpenACC implementation name
- scenario id
- correctness or equivalence status
- primary metric on both sides
- whether the result is benchmark-only or benchmark-plus-profiler
- dominant phase or transfer source if known
- next action

## Mutex Rule

Serialize benchmark-producing or profiler-producing runs on shared hosts.

If a repo already has a benchmark mutex helper, use it. If not, borrow the pattern from `compare-benchmarks` instead of improvising a new rule each time.

## Summary-First Rule

Read compact summaries first.

Only inspect raw profiler artifacts when the summaries disagree or remain inconclusive.

Use profiling only when timing deltas need explanation:

- transfer or staging overhead
- synchronization gaps
- launch trains
- one kernel class becoming dominant

## When To Use `compare-benchmarks`

Route into `compare-benchmarks` when:

- the repo needs a real A/B harness
- wrappers must normalize two different benchmark entrypoints
- component-by-component breakdowns need stable comparison artifacts
- the problem is now fair benchmarking rather than OpenACC porting
