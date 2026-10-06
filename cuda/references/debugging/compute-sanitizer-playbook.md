# Compute Sanitizer Playbook

Use this file when the crash route has already decided the next move is `compute-sanitizer`.

## Default Tool Order

- `memcheck`: default first pass for illegal access, invalid pointers, and memory corruption
- `initcheck`: use when behavior depends on uninitialized device data
- `synccheck`: use when barriers, warp sync, or cooperative assumptions look wrong
- `racecheck`: use when concurrent updates or shared-memory races are plausible

## Wrapper

Use:

```bash
scripts/debug_compute_sanitizer.sh --tool memcheck -- ./your_bin
```

Read `summary.txt` first. It should tell you whether the run is conclusive, what failure family was detected, and whether the next step is a fix or a `cuda-gdb` escalation.

If the summary reports `sanitizer-device-unsupported`, treat the run as limited:

- the wrapper may still recover a useful crash family and saved host frames
- do not mistake that for full device-side instrumentation
- prefer `CUDA_LAUNCH_BLOCKING=1` or batch `cuda-gdb` next if you still need the exact failing operation

## Rules

- keep the reproducer minimal and deterministic before running a heavier sanitizer pass
- use `memcheck` first unless race or sync symptoms are already obvious
- prefer one tool at a time; do not collect every sanitizer mode unless the summary tells you the first pass was inconclusive
- treat `cuda-memcheck` as compatibility fallback, not the primary route, when `compute-sanitizer` is available

## What To Do With The Result

- conclusive memory fault: fix pointer arithmetic, indexing, or lifetime before deeper profiling
- conclusive race or sync fault: repair the synchronization contract before benchmarking
- limited sanitizer support on this host: use the host frames as a hint, then rerun with a simpler reproducer or a debugger path that still works here
- clean sanitizer but persistent crash: escalate to batch `cuda-gdb`
