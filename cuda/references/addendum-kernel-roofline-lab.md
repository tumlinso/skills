# Addendum: Kernel Roofline Lab

Use this addendum after the broad design choices are already reasonable and the remaining problem is how to move a hot kernel materially closer to the practical V100 limit.

The first gate is now simple:

- if `profile_nsys.sh` says the run is not representative of steady state, fix the benchmark window first
- if `profile_ncu.sh` says the counters are valid, use its `summary.txt` to choose the limiter before touching code

## Workflow

1. Confirm the measurement is worth tuning.
   - Nsight Systems summary must say the run is usable for the question being asked.
   - Nsight Compute summary must say the counters are valid.

2. Classify the kernel.
   - memory-bound
   - compute-heavy
   - register-limited
   - shared-memory-limited
   - launch-bound only when Nsight Systems still shows a short-kernel train

3. Compare against the right ceiling.
   - bandwidth ceiling for memory-bound kernels
   - Tensor Core or SM throughput ceiling for dense compute kernels
   - launch overhead ceiling for tiny-kernel trains

4. Apply only the levers that match the limiter.
   - do not chase occupancy when the summary says memory-bound
   - do not chase Tensor Cores when bytes moved dominate
   - do not trust Nsight Compute runtime for throughput deltas

5. Re-measure after every meaningful change.
   - benchmark for throughput
   - Nsight Systems for whether the run window is clean
   - Nsight Compute for why the hot kernel still behaves that way

6. Resume the main `cuda` workflow if the right answer is to replace the kernel with a library path or to change the wider system decomposition.

## Support References

- Read `references/roofline-playbook.md` for the limiter-to-action map.
- Read `references/roofline-counter-triage.md` for counter patterns and what each implies on V100.
- Read `references/roofline-launch-bound-patterns.md` when the timeline is dominated by many tiny kernels or graph-capture candidates.
- Read `references/roofline-cutlass-vs-handwritten.md` when deciding whether to keep tuning a custom dense kernel or replace it with CUTLASS or cuBLASLt.
- Read `references/roofline-example-tuning-loops.md` for concrete counter-driven tuning sequences and stopping rules.

## Output Requirements

Be explicit about:

- whether the profiler summary says the measurement is representative
- the current limiter
- the ceiling being compared against
- which lever is being changed and why
- what measurement would prove the change helped
