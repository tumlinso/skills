

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-40: Repin and cut over the corrected Project Control read provider

Task revision: `786`; current project revision is in `todo-status.md`.

## Objective
Consume the ordinary forward Project Control remediation commit, rebuild the candidate, atomically update the existing project-control service and sole Codex registration, and prove all registered Todo authorities including the Cellerator sentinel through observer-only reads.

## State
- Lifecycle: `blocked`
- Execution: `blocked_dependency`
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
- `read`: `todo-orchestrator`
- `read`: `unification/pcu-v1/contracts`
- `read`: `unification/pcu-v1/scripts`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
