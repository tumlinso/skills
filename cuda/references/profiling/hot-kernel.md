# Tune A Proven Hot Kernel

Use this guide after architecture, library choice, data layout, and kernel structure are reasonable and one representative hot kernel remains. It is written around the native V100 toolchain; use the selected architecture route for family-specific counters and limits elsewhere.

Before executing correctness, benchmark, or profiler work on the shared host, read [host execution](../execution/host-execution.md). Controller admission owns the run; profiling and benchmark wrappers supply capture/serialization behavior inside that admitted run. A mutex wrapper alone is not host admission.

The first gate is now simple:

- if `profile_nsys.sh` says the run is not representative of steady state, fix the benchmark window first
- if `profile_ncu.sh` says the counters are valid, use its `summary.txt` to choose the limiter before touching code

## Diagnose and tune

1. Confirm the measurement is worth tuning.
   - Nsight Systems summary must say the measured window is usable for the question.
   - Nsight Compute summary must say the counters are valid; treat NCU replay/runtime as diagnostic evidence, not a throughput measurement.

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
   - do not use Nsight Compute replay/runtime for throughput deltas; compare unprofiled benchmark runs for speed

5. Re-measure after every meaningful change.
   - benchmark for throughput
   - Nsight Systems for whether the run window is clean
   - Nsight Compute for why the hot kernel still behaves that way

6. If evidence points to the wrong library boundary or wider pipeline/topology, route to [compute-library selection](../common/compute-libraries.md) or the relevant system guide rather than continuing local kernel tuning.

## Route by evidence

- Use [roofline actions](roofline-playbook.md) to map the diagnosed limiter to a lever.
- Use [counter triage](roofline-counter-triage.md) when NCU counters remain ambiguous or contradictory.
- Use [launch-bound patterns](roofline-launch-bound-patterns.md) when Systems shows a short-kernel train or graph-capture opportunity.
- Use [CUTLASS versus handwritten](roofline-cutlass-vs-handwritten.md) when dense custom-kernel tuning competes with a library/template path.
- Use [example tuning loops](roofline-example-tuning-loops.md) when you need a concrete measurement sequence or stop condition.
- If the limiter is actually pipeline starvation, transfer, or multi-GPU topology, return to the system-level route instead of tuning this kernel.

## Output Requirements

Be explicit about:

- whether the profiler summary says the measurement is representative
- the current limiter
- the ceiling being compared against
- which lever is being changed and why
- what measurement would prove the change helped
