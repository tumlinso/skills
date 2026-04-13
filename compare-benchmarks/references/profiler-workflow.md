# Profiler Workflow

Use this reference when benchmark timing alone is not enough.

## Summary-First Rule

Always produce compact profiler summaries first.

Only inspect raw profiler artifacts when the summary is inconclusive.

## Nsight Systems Workflow

Use:

- `scripts/profile_compare_nsys.sh`

Questions it should answer:

- is the slowdown in transfer, synchronization, launch trains, or idle gaps
- do both sides have the same steady-state window
- which side has worse overlap or staging behavior

## Nsight Compute Workflow

Use:

- `scripts/profile_compare_ncu.sh`

Questions it should answer:

- which side has the hotter kernel class
- whether the slower side is more memory-bound, launch-bound, or register-limited
- whether the dominant kernel class differs between A and B

## Combined Summary

After profiling:

- run `scripts/combine_compare_summaries.py`
- read `combined_summary.txt` first

The combined summary should stay concise enough to load directly into context.
