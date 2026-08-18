# ASan UBSan TSan Playbook

Use this file after `sanitizer-builds.md`.

## Choose The Smallest Useful Sanitizer

- `ASan`: memory lifetime and bounds bugs
- `UBSan`: undefined behavior and invalid assumptions
- `TSan`: data races and synchronization misuse

## Readouts To Trust

Treat these as high-signal:

- the first reported failing access
- the allocation and free stack around a use-after-free
- the exact runtime error line from `UBSan`
- the first `TSan` race report, not the long tail after it

## Readouts To Treat Carefully

- secondary crashes after the first sanitizer report
- deep allocator internals when the first user frame is already visible
- repeated race reports from the same root cause

## Suggested Workflow

1. Rebuild with one sanitizer family.
2. Run the reproducer under `scripts/debug_crash.sh`.
3. Read the generated summary first.
4. If the summary is conclusive, fix the first high-signal report.
5. Rerun the same instrumented build before switching tools.

## Environment Notes

Useful runtime settings:

```bash
ASAN_OPTIONS=abort_on_error=1:symbolize=1
UBSAN_OPTIONS=print_stacktrace=1
TSAN_OPTIONS=halt_on_error=1
```

If `llvm-symbolizer` is unavailable, install it or point the sanitizer runtime at the correct symbolizer path.

## Exit Criteria

Leave this route when:

- the failing source line is clear enough to fix
- the instrumented binary stops reproducing and you need a different route
- the issue is clearly CUDA-side and belongs in `cuda`
