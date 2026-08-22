

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-19: Final release validation and handoff

Task revision: `242`; current project revision is in `todo-status.md`.

## Objective
Run one complete release validation, verify backward compatibility, clean resource recovery, real host profile, bounded skill surfaces, generated projections, and concise operator workflows; export the final snapshot and leave no stale claims or runtime ownership.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `project_exclusive`
- Result: `validated`

## Next Action
Run the single full release gate, inspect only failures, fix regressions narrowly, export the todo snapshot, and publish a compact handoff.

## Ownership
- `exclusive`: `.gitignore`
- `exclusive`: `.todo-orchestrator/state.snapshot.json`
- `exclusive`: `AGENTS.md`
- `exclusive`: `core4-tests/release`
- `exclusive`: `cpp-context-compiler/SKILL.md`
- `exclusive`: `cuda/SKILL.md`
- `exclusive`: `local-coding-worker/SKILL.md`
- `exclusive`: `scripts/core4_validate.py`
- `exclusive`: `todo-orchestrator/SKILL.md`
- `exclusive`: `todo-status.md`
- `exclusive`: `todos.md`
- `read`: `contracts`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `local-coding-worker`
- `read`: `todo-orchestrator`

## Dependencies
- `barrier`: `CORE4-RELEASE-CANDIDATE`
<!-- todo-orchestrator:v2-managed:end -->
