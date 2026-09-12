<!-- todo-orchestrator:v2-managed:start -->
# SK-WF2-D02: Preserve host-wide admission and lease behavior

Task revision: `797`; current project revision is in `todo-status.md`.

## Objective
Rewire host coordinator access without creating a second host resource authority. Verify CPU/RAM/GPU request semantics, preemption, quiescence, PID incarnation and release on failures.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `parallel_safe`
- Result: `-`

## Next Action
Read planning/workflow-foundation-v2/proposed-todos/sk-wf2-d02.md; verify live prerequisites and evidence before work.

## Ownership
- `exclusive`: `cuda/scripts`
- `exclusive`: `cuda/tests`
- `exclusive`: `local-coding-worker/local_worker`
- `exclusive`: `local-coding-worker/scripts`
- `exclusive`: `local-coding-worker/tests`
- `exclusive`: `tests/wf2_acceptance/d`
- `read`: `planning/workflow-foundation-v2`

## Dependencies
- `task`: `SK-WF2-D01`
<!-- todo-orchestrator:v2-managed:end -->
