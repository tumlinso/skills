

<!-- todo-orchestrator:v2-managed:start -->
# CWM-07: Fix bounded delegation target and scope translation

Task revision: `91`; current project revision is in `todo-status.md`.

## Objective
Treat MCP target text as a delegation objective, derive or omit a separately proven ctxpp target, and select 1-16 relevant child scopes within the parent authorization for writable and read-only CE-style requests without weakening admission or acceptance safety.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `integrations/coding-workflow-mcp`
- `exclusive`: `local-coding-worker`
- `read`: `cpp-context-compiler`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CWM-06`
<!-- todo-orchestrator:v2-managed:end -->
