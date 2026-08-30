

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-21: Add and pin the Project Control Git submodule

Task revision: `761`; current project revision is in `todo-status.md`.

## Objective
Consume the validated standalone release, verify manifest/digests, add the legitimate remote as project-control, and record the exact pin; block if release is missing.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `.gitmodules`
- `exclusive`: `project-control`
- `exclusive`: `unification/pcu-v1/PCU_RELEASE.lock.json`
- `exclusive`: `unification/pcu-v1/scripts/pcu_harness.py`
- `read`: `unification/pcu-v1/contracts`

## Dependencies
- `task`: `PCU-SK-20`
<!-- todo-orchestrator:v2-managed:end -->
