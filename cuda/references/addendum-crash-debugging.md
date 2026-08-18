# Addendum: Crash Debugging

Use this addendum when a CUDA or CUDA-adjacent binary crashes before normal profiler-driven tuning can begin.

Use it for:

- host-visible segmentation faults
- CUDA illegal memory access
- device-side asserts and traps
- launch failures or invalid-configuration faults
- sanitizer-detectable memory, init, or sync issues
- requests to use `compute-sanitizer`, `cuda-memcheck`, or `cuda-gdb`

## Workflow

1. Capture one compact first-pass crash summary with `scripts/debug_crash.sh`.
2. Classify the crash surface before choosing a tool:
   - memory-style failure -> `scripts/debug_compute_sanitizer.sh --tool memcheck`
   - race or sync suspicion -> `scripts/debug_compute_sanitizer.sh --tool racecheck` or `--tool synccheck`
   - still ambiguous after the sanitizer pass -> `scripts/debug_cuda_gdb.sh`
3. Treat debugger limitations as first-class output:
   - if `compute-sanitizer` reports `Device not supported`, use its host frames only as crash-family evidence
   - if `cuda-gdb` detaches after a fork or exits with `No stack`, rerun on the child process path rather than trusting the empty backtrace
4. Read `summary.txt` or `combined_summary.txt` first. Do not open raw logs until the summary says the result is inconclusive.
5. Return to profiler or optimization routes only after the binary runs stably enough to measure representative behavior.

## Read Next

- `references/crash-triage-playbook.md`
- `references/compute-sanitizer-playbook.md`
- `references/cuda-gdb-playbook.md`
- `references/crash-signature-map.md`

## Output Requirements

Be explicit about:

- crash class
- likely domain: host crash, device memory bug, race or sync bug, init bug, launch issue, or unknown
- whether the result is conclusive
- the recommended next tool or next fix
- which summary file should be read first
