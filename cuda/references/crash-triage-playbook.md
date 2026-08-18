# Crash Triage Playbook

Use this file after `addendum-crash-debugging.md` when the first job is to classify the failure quickly.

## First Pass

Run `scripts/debug_crash.sh` first.

Trust its `summary.txt` to tell you:

- exit code or signal
- whether the process crashed before CUDA initialization, during a CUDA API call, or after a device-side failure message
- whether the next move should be sanitizer, `cuda-gdb`, or a simple rerun with a cleaner debug build

## Decision Rules

Use `compute-sanitizer` next when:

- stderr mentions illegal memory access, misaligned address, invalid address space, or warp out-of-range access
- the binary aborts after a kernel launch with no clear host backtrace
- the failure likely comes from data races, uninitialized values, or synchronization misuse

Use batch `cuda-gdb` next when:

- the program segfaults immediately with no useful CUDA error
- sanitizer runs clean but the crash persists
- you need a short backtrace or failing source line

Do not start with profilers when the binary still crashes during warmup or setup.

## Likely Failure Families

- host segfault: often pointer or lifetime bug on the CPU side, or a bad host callback path
- illegal memory access: most often out-of-bounds or invalid device pointer use
- device assert or trap: often a violated kernel assumption or explicit debug assertion
- invalid configuration or launch failure: often bad launch geometry, shared-memory size, or kernel parameter mismatch
- race or sync issue: usually requires `racecheck` or `synccheck`

## Minimal Build Guidance

For crash reproduction builds, prefer:

- `-g -G` when you need device-debug visibility and can tolerate slower runs
- `-lineinfo` when you want source correlation with less perturbation
- frame pointers on the host side so backtraces stay readable

Use release profiling builds only after the crash path is stabilized.
