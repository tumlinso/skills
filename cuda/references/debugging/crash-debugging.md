# CUDA Crash Triage

Use this guide when a CUDA or CUDA-adjacent binary crashes before representative profiling. Classify the failure and establish a stable run before performance work.

Use it for:

- host-visible segmentation faults
- CUDA illegal memory access
- device-side asserts and traps
- launch failures or invalid-configuration faults
- sanitizer-detectable memory, init, or sync issues
- requests to use `compute-sanitizer`, `cuda-memcheck`, or `cuda-gdb`

Before executing debug captures on the shared host, follow [host execution](../execution/host-execution.md). Start with one compact capture; inspect `summary.txt` or `combined_summary.txt` before opening raw logs.

## Triage

1. Capture one compact first-pass crash summary with `scripts/debug_crash.sh`.
2. Classify the crash surface before choosing a tool:
   - memory-style failure -> `scripts/debug_compute_sanitizer.sh --tool memcheck`
   - race or sync suspicion -> `scripts/debug_compute_sanitizer.sh --tool racecheck` or `--tool synccheck`
   - still ambiguous after the sanitizer pass -> `scripts/debug_cuda_gdb.sh`
3. Treat debugger limitations as first-class output:
   - if `compute-sanitizer` reports `Device not supported`, use its host frames only as crash-family evidence
   - if `cuda-gdb` detaches after a fork or exits with `No stack`, rerun on the child process path rather than trusting the empty backtrace
4. Return to profiling only after the binary runs stably enough for representative measurement.

Use [crash signatures](crash-signature-map.md) to map first-pass evidence to a likely fault family. For a memory, initialization, race, or sync hypothesis, use the matching [Compute Sanitizer playbook](compute-sanitizer-playbook.md) first. Escalate to the [cuda-gdb playbook](cuda-gdb-playbook.md) when sanitizer output is clean or inconclusive and an exact failing operation is still needed. Use [crash triage](crash-triage-playbook.md) when first-pass evidence does not distinguish host, launch, or device failure.

## Output Requirements

Be explicit about:

- crash class
- likely domain: host crash, device memory bug, race or sync bug, init bug, launch issue, or unknown
- whether the result is conclusive
- the recommended next tool or next fix
- which summary file should be read first
