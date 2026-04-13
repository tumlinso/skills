# Debug Workflow

Use this file first.

## Default Sequence

1. Reproduce the failure with the smallest stable command.
2. Run `scripts/debug_crash.sh -- ./your_bin ...`.
3. Read `summary.txt` before opening raw logs.
4. Pick one follow-on route:
   - sanitizer rebuild for memory, UB, or race suspicion
   - batch `gdb` for a short backtrace
   - symbolization for raw addresses or mangled names
   - `strace` for path, permission, loader, or process-boundary trouble
   - `perf` for CPU-side runtime diagnosis on a stable run
5. Combine summaries only if two passes are genuinely complementary.

## Decision Rules

Use sanitizer builds next when:

- the crash looks like memory corruption, undefined behavior, or a race
- the process aborts without a useful source line
- you can rebuild the target with debug-friendly flags

Use `gdb` next when:

- the process dies with `SIGSEGV`, `SIGABRT`, `SIGBUS`, `SIGILL`, or `SIGFPE`
- you need a short backtrace or source line quickly
- the sanitizer rerun still leaves the failing site unclear

Use symbolization next when:

- you already have raw PCs, offsets, or mangled names
- the backtrace exists but source paths are missing
- you need to map stripped frames back to a binary or shared object

Use `strace` next when:

- startup fails before your own logging appears
- a file, socket, process, or loader problem is likely
- you suspect a missing runtime dependency or wrong search path

Use `perf` next when:

- the program runs stably enough to measure
- the user wants a fast CPU-side diagnosis, not a full benchmark harness
- you need to know whether the process is instruction-heavy, branchy, or stalled before deeper profiling

Route to CUDA follow-on when:

- stderr or logs mention CUDA runtime or driver failures
- the user explicitly asks for `compute-sanitizer`, `cuda-gdb`, Nsight Systems, or Nsight Compute
- the host backtrace only shows CUDA launch or synchronization boundaries and the real fault is on the device side

## Build Baseline

Prefer debug-friendly reproducer builds:

- `-g -O0 -fno-omit-frame-pointer` for first-pass host debugging
- add sanitizers only for the specific fault family you are chasing
- avoid mixing every sanitizer at once unless you are explicitly testing compatibility

Do not start with `perf` or benchmark work while the program still crashes.
