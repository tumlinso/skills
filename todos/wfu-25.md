

<!-- todo-orchestrator:v2-managed:start -->
# WFU-25: Remove obsolete protocol discovery and child-independence guidance

Task revision: `231`; current project revision is in `todo-status.md`.

## Objective
Update the installed two-worker smoke to the exact six-tool protocol and coordinate_task gate action, remove residual wording that describes subordinate local-worker children as independent project work, and add focused regression coverage.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `validated`

## Next Action
_None._

## Ownership
- `exclusive`: `integrations/coding-workflow-mcp/scripts/live_two_readonly_smoke.py`
- `exclusive`: `integrations/coding-workflow-mcp/tests/test_protocol.py`
- `exclusive`: `local-coding-worker/SKILL.md`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/mcp/server.py`

## Dependencies
- `task`: `WFU-21`
<!-- todo-orchestrator:v2-managed:end -->
