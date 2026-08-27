

<!-- todo-orchestrator:v2-managed:start -->
# WFU-31: Atomic cutover, installed smoke, rollback proof, and release

Task revision: `194`; current project revision is in `todo-status.md`.

## Objective
After the release rendezvous and renewed quiescence check, integrate the validated branch, atomically install and register the canonical package and shim, verify exact six-tool discovery and disposable workflow/recovery/project-control smokes, roll back on failure, finalize documentation, and leave every repository clean.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `project_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `workflow-unification/evidence/release`
- `exclusive`: `workflow-unification/rollback.md`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator`
- `read`: `workflow-unification`

## Dependencies
- `barrier`: `WFU-RELEASE-RENDEZVOUS`
<!-- todo-orchestrator:v2-managed:end -->
