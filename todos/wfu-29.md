

<!-- todo-orchestrator:v2-managed:start -->
# WFU-29: Harden installed canonical locator and package rollback

Task revision: `243`; current project revision is in `todo-status.md`.

## Objective
Fix the installed owner command to locate the canonical todo package without MCP-only environment variables, and preserve the complete prior installed package as a recoverable rollback artifact during cutover.

## State
- Lifecycle: `in_progress`
- Execution: `claimed`
- Parallel policy: `project_exclusive`
- Result: `-`

## Next Action
_None._

## Ownership
- `exclusive`: `integrations/coding-workflow-mcp/coding_workflow_mcp/_canonical.py`
- `exclusive`: `integrations/coding-workflow-mcp/scripts/install.py`
- `exclusive`: `integrations/coding-workflow-mcp/tests/test_installer.py`
- `read`: `integrations/coding-workflow-mcp`
- `read`: `todo-orchestrator/todo_orchestrator/workflow/admin.py`

## Dependencies
- `task`: `WFU-30`
<!-- todo-orchestrator:v2-managed:end -->
