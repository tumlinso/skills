

<!-- todo-orchestrator:v2-managed:start -->
# CWM-10: Preflight bounded source context before local delegation

Task revision: `125`; current project revision is in `todo-status.md`.

## Objective
Ensure coding-workflow establishes or proves a usable bounded ctxpp packet before local-worker child creation and admission, serializes safe first-use initialization, fails early without leases or model startup, and proves a delegated disposable read-only request reaches actual worker execution.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `cpp-context-compiler`
- `exclusive`: `integrations/coding-workflow-mcp`
- `exclusive`: `local-coding-worker`
- `read`: `cuda`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CWM-09`
<!-- todo-orchestrator:v2-managed:end -->
