

<!-- todo-orchestrator:v2-managed:start -->
# SK-WF2-C01: Expose read-only indexed ctxpp queries

Task revision: `878`; current project revision is in `todo-status.md`.

## Objective
Create a small stable query facade over existing query.sqlite/manifest, supporting exact symbol ID, qualified name, canonical range and typed graph edges. No scanning or publication is permitted by this operation.

## State
- Lifecycle: `superseded`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `superseded`

## Next Action
Read planning/workflow-foundation-v2/proposed-todos/sk-wf2-c01.md; verify live prerequisites and evidence before work.

## Ownership
- `exclusive`: `cpp-context-compiler/references`
- `exclusive`: `cpp-context-compiler/schemas`
- `exclusive`: `cpp-context-compiler/scripts`
- `exclusive`: `cpp-context-compiler/tests`
- `exclusive`: `tests/wf2_acceptance/c`
- `read`: `planning/workflow-foundation-v2`

## Dependencies
- `task`: `SK-WF2-X01`
<!-- todo-orchestrator:v2-managed:end -->
