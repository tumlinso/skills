<!-- todo-orchestrator:v2-managed:start -->
# SK-WF2-V04: Verify final migration after the release switch

Task revision: `797`; current project revision is in `todo-status.md`.

## Objective
After actual deployed receipt, run bounded read/import smoke with new release and observe old-entry compatibility without mutating unrelated authorities. Verify retained rollback and source closure.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
Read planning/workflow-foundation-v2/proposed-todos/sk-wf2-v04.md; verify live prerequisites and evidence before work.

## Ownership
- `exclusive`: `docs/workflow_foundation_v2/validation`
- `exclusive`: `tests/wf2_acceptance/v`
- `exclusive`: `tests/wf2_validation`
- `read`: `planning/workflow-foundation-v2`

## Dependencies
- `task`: `SK-WF2-X03`
- `task`: `SK-WF2-I60`
<!-- todo-orchestrator:v2-managed:end -->
