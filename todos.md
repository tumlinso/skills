# Active Objectives

## Summary
Use this file as the canonical index for substantial multi-step work.

## Shared Assumptions
_None recorded yet._

## Suggested Skills
- `cuda-v100`

## Useful Reference Files
- `cuda-v100/references/benchmark-standardization.md`
- `cuda-v100/references/benchmark-target-authoring.md`

## Workstreams
- `todos/cuda-v100-benchmark-mutex.md`: Completed. Baked a shared benchmark mutex into the `cuda-v100` skill so concurrent agents serialize benchmark and profiler runs.

## Global Blockers
_None recorded yet._

## Progress Notes
- Bootstrapped the `todo-orchestrator` workflow ledger for this repo.
- Started the `cuda-v100` benchmark mutex workstream and scoped the integration to shared script plumbing plus benchmark authoring docs.
- Added `scripts/with_benchmark_mutex.sh`, routed both profiler wrappers through it, and verified syntax plus a live contention test with a temporary lock file.

## Next Actions
- Create or resume a new workstream ledger when the next substantial repo task arrives.

## Done Criteria
- Every active workstream in `todos/` is reflected here with a current status.
- The `cuda-v100` benchmark path serializes measurement runs through a shared mutex and the skill docs say how to use it for raw benchmark commands.
