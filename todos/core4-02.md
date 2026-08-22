

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-02: Freeze behavior and compatibility baselines

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Capture the exact existing public behavior of todo-orchestrator, cuda, and cpp-context-compiler before semantic changes, including CLI commands, JSON envelopes, core tests, performance fixture identities, and substantive guidance preservation requirements.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `validated`

## Next Action
After CORE4-02A resolves the ctxpp baseline contract and freezes CORE4-BASELINE-FROZEN, resume only to verify and close the baseline task.

## Ownership
- `exclusive`: `contracts/core4-compatibility-v1.json`
- `exclusive`: `core4-tests/baseline`
- `forbidden`: `local-coding-worker`
- `read`: `AGENTS.md`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `todo-orchestrator`

## Dependencies
- `task`: `CORE4-01`
- `task`: `CORE4-02A`
<!-- todo-orchestrator:v2-managed:end -->
