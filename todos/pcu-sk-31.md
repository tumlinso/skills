

<!-- todo-orchestrator:v2-managed:start -->
# PCU-SK-31: Rehearse downstream migration in independent clones

Task revision: `739`; current project revision is in `todo-status.md`.

## Objective
Rehearse dry-run, apply, idempotent reapply, and remove in genuinely independent clones; never touch a real downstream checkout or Todo authority.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `unification/pcu-v1/evidence/migration/pcu-sk-31.migration.json`
- `forbidden`: `Baseplane`
- `forbidden`: `BioPrep`
- `forbidden`: `C4Q-01`
- `forbidden`: `CellShard`
- `forbidden`: `Cellerator`
- `forbidden`: `GlassHelix`
- `forbidden`: `todos/C4Q-01.md`
- `forbidden`: `workflow-unification/evidence`
- `read`: `project-control/src/project_control/migration.py`
- `read`: `project-control/tests/test_migration.py`
- `read`: `project-control/unification/pcu-v1/contracts/downstream-migration.md`
- `read`: `unification/pcu-v1/fixtures`
- `read`: `unification/pcu-v1/scripts`

## Dependencies
- `task`: `PCU-SK-22`
<!-- todo-orchestrator:v2-managed:end -->
