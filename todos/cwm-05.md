

<!-- todo-orchestrator:v2-managed:start -->
# CWM-05: Rebase onto the repaired skills and validate the live public contracts

Task revision: `100`; current project revision is in `todo-status.md`.

## Objective
Integrate the user's latest local-worker repair, validate todo/ctxpp/local-worker/CUDA adapters, run one real read-only MCP delegation, one bounded writable delegation, and preserve immediate local-unavailable fallback.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `AGENTS.md`
- `exclusive`: `integrations/coding-workflow-mcp`
- `exclusive`: `local-coding-worker`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CWM-03`
- `task`: `CWM-04`
<!-- todo-orchestrator:v2-managed:end -->
