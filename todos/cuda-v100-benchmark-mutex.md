# CUDA V100 Benchmark Mutex

## Objective Summary
Bake a shared benchmark mutex into the `cuda-v100` skill so concurrent agents do not overlap benchmark or profiler runs and skew measurements.

## Planning Notes
- The skill-owned benchmark-running scripts are `scripts/profile_nsys.sh` and `scripts/profile_ncu.sh`.
- Repo-local benchmark binaries are external to the skill, so the skill also needs a reusable wrapper for raw benchmark commands.
- The mutex should be host-global by default and configurable through an environment variable.

## Assumptions And Defaults
- Default mutex path: `${CUDA_V100_BENCHMARK_MUTEX_PATH:-${TMPDIR:-/tmp}/cuda_v100_benchmark.lock}`.
- The mutex should block and wait rather than fail fast.
- The lock only needs to cover the measurement-producing command, not post-run summary parsing.

## Concrete Implementation Steps
1. Add a shared `with_benchmark_mutex.sh` helper under `cuda-v100/scripts/`.
2. Route `profile_nsys.sh` through the helper for the actual profiling command.
3. Route `profile_ncu.sh` through the helper for the actual profiling command.
4. Update `SKILL.md` and benchmark references so raw benchmark commands use the same wrapper or embed an equivalent lock.
5. Run shell syntax checks on the modified scripts.

## Validation And Test Plan
- Run `bash -n` on the modified shell scripts.
- Inspect help text and workflow docs for a clear raw-benchmark usage example.

## Blockers And External Dependencies
- None.

## Suggested Skills
- `cuda-v100`

## Useful Reference Files
- `cuda-v100/references/benchmark-standardization.md`
- `cuda-v100/references/benchmark-target-authoring.md`

## Next Actions
- None. Validation passed and the workstream is complete.

## Done Criteria
- The skill contains a reusable benchmark mutex helper.
- The profiler wrappers serialize their benchmark-producing runs through that helper.
- The benchmark references tell authors and agents how to serialize raw benchmark commands too.

## Completion Notes
- Added `cuda-v100/scripts/with_benchmark_mutex.sh`.
- Wired `profile_nsys.sh` and `profile_ncu.sh` through the shared mutex helper.
- Updated `SKILL.md`, benchmark references, and `agents/openai.yaml` so the benchmark mutex is part of the skill contract.
- Verified with `bash -n` and a live two-process contention test using a temporary lock file.
