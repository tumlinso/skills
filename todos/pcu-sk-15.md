

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-15: Build fresh-clone, release-pin, and migration rehearsal harnesses

Task revision: `288`; current project revision is in `todo-status.md`.

## Objective
Build deterministic manifest, recursive clone, candidate install, registration rollback, and independent downstream-clone verification without live mutation.

## State
- Lifecycle: `in_progress`
- Execution: `idle`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `.github/workflows/project-control-unification.yml`
- `exclusive`: `tests/pcu_v1`
- `exclusive`: `unification/pcu-v1/fixtures`
- `exclusive`: `unification/pcu-v1/scripts`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `checkpoint`: `PCU-SK-CONTRACTS-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
