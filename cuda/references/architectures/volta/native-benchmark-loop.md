# Native V100 Benchmark Loop

Use this route when the question is how to benchmark, profile, and recompile on
the native V100 host without losing signal inside wide binaries or noisy logs.

## Native Loop

1. Keep one hot kernel per TU when deep tuning.
2. Emit a narrow `sm_70` profile build.
3. Add `small`, `large-compute`, `large-transfer`, and `real` scenarios only
   after the harness is stable.
4. Keep profiler and dump summaries compact enough that another agent can read
   them without opening raw artifacts.

## Script Surface

- `scripts/architectures/volta/emit_profile_build.py`
- `scripts/architectures/volta/gen_native_bench_matrix.py`
- `scripts/profile_nsys.sh`
- `scripts/profile_ncu.sh`
- `scripts/with_benchmark_mutex.sh`

## Scenario Notes

- `small`: expose launch and glue overhead
- `large-compute`: saturate math or Tensor Core candidates
- `large-transfer`: expose staging and PCIe pain
- `real`: preserve sparse skew, branch shape, and topology behavior

## Native Rule

Do not use a mixed-architecture binary for deep native benchmarking unless the
question is explicitly about portability cost.
