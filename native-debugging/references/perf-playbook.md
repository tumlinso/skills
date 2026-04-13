# Perf Playbook

Use this file only after the program runs stably enough to measure.

## Wrapper

Use:

```bash
scripts/debug_perf.sh -- ./your_bin
```

The wrapper should emit:

- `summary.txt`
- `summary.json`
- `perf_stat.csv`
- target `stdout.txt` and `stderr.txt`

## What This Route Is For

This route is for a fast CPU-side diagnosis, not full benchmark design.

Use it to answer questions like:

- is the run mostly cycles, instructions, or branch-heavy work
- is IPC obviously low
- is the binary stable enough to justify deeper profiling

## Practical Rules

- start with `perf stat`, not `perf record`
- use the default counters first
- treat permission failures as environment issues, not performance findings
- if the user needs fair A/B timing across two implementations, route to `compare-benchmarks` instead of growing this skill into a benchmark harness
