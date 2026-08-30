

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-41: Retry the corrected read-port candidate cutover

Task revision: `787`; current project revision is in `todo-status.md`.

## Objective
Consume the validated Project Control capability-remediation release, repin the existing submodule, rebuild and atomically cut over the candidate, and prove the complete Cellerator sentinel solely through observer reads.

## State
- Lifecycle: `in_progress`
- Execution: `claimed`
- Parallel policy: `integration_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `project-control`
- `exclusive`: `unification/pcu-v1/PCU_RELEASE.lock.json`
- `exclusive`: `unification/pcu-v1/evidence/read-port-remediation`
- `forbidden`: `Baseplane`
- `forbidden`: `BioPrep`
- `forbidden`: `C4Q-01`
- `forbidden`: `CellShard`
- `forbidden`: `Cellerator`
- `forbidden`: `GlassHelix`
- `forbidden`: `todos/C4Q-01.md`
- `forbidden`: `workflow-unification/evidence`
- `read`: `.gitmodules`
- `read`: `pcu-v1-read-port-remediation.plan.json`
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1/contracts`
- `read`: `unification/pcu-v1/scripts`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
