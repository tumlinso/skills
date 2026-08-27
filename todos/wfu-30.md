

<!-- todo-orchestrator:v2-managed:start -->
# WFU-30: Full compatibility, concurrency, recovery, MCP, observation, and dogfood validation

Task revision: `171`; current project revision is in `todo-status.md`.

## Objective
Run all existing and new unit/integration suites and execute the complete disposable parallel-run dogfood scenario with machine-readable evidence, including lane serialization, parent-mediated local delegation, rendezvous, workspace integration/conflict, recovery, bounded context, and secret exclusion.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `project_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `todo-orchestrator/tests/test_workflow_dogfood.py`
- `exclusive`: `workflow-unification/dogfood`
- `exclusive`: `workflow-unification/evidence/validation`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator`
- `read`: `workflow-unification`

## Dependencies
- `task`: `WFU-20`
- `task`: `WFU-21`
- `task`: `WFU-22`
- `task`: `WFU-23`
<!-- todo-orchestrator:v2-managed:end -->
