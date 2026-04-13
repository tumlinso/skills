# Comparison Contract

Use this reference to define the shared run contract for implementation A and implementation B.

## Required Top-Level Artifacts

Every comparison run should produce:

- `compare_config.json`
- `summary.json`
- `summary.txt`

Each side should also produce:

- `impl_a/run_config.json`
- `impl_a/results.json`
- `impl_b/run_config.json`
- `impl_b/results.json`

If profiled, also produce:

- `impl_a/nsys/summary.json`
- `impl_b/nsys/summary.json`
- `impl_a/ncu/summary.json`
- `impl_b/ncu/summary.json`
- `combined_summary.json`
- `combined_summary.txt`

## Required Comparison Config

`compare_config.json` should minimally include:

```json
{
  "comparison_id": "liba-vs-libb",
  "impl_a_name": "liba",
  "impl_b_name": "libb",
  "scenario_id": "large-compute",
  "warmup": 1,
  "repeats": 5,
  "profile_friendly": true,
  "mutex_path": "/tmp/compare_benchmarks.lock"
}
```

## Required Summary Fields

The comparison summary should report:

- implementation names
- scenario id
- correctness or equivalence status
- status
- steady-state validity
- primary metric on both sides
- percent delta
- dominant phase on both sides
- top explanation for the difference
- next action

## Mutex Rule

All benchmark-producing runs must be serialized with the skill mutex:

- wrapper: `scripts/with_benchmark_mutex.sh`
- env override: `COMPARE_BENCHMARK_MUTEX_PATH`

Profiler and non-profiler runs must share the same lock path.
