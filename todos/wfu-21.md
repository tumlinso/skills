

<!-- todo-orchestrator:v2-managed:start -->
# WFU-21: Rewrite routing, installer, migration, and operations documentation

Task revision: `201`; current project revision is in `todo-status.md`.

## Objective
Enforce one front door, add workflow_front_door compatibility policy, reduce the integration path to installer/shim/migration/tests, provide idempotent repository migration, document protocol, lanes versus children, recovery, rollback, and remove obsolete normal-workflow guidance.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
_None._

## Ownership
- `exclusive`: `AGENTS.md`
- `exclusive`: `cpp-context-compiler/SKILL.md`
- `exclusive`: `cuda/SKILL.md`
- `exclusive`: `integrations/coding-workflow-mcp`
- `exclusive`: `local-coding-worker/SKILL.md`
- `exclusive`: `todo-orchestrator/SKILL.md`
- `exclusive`: `todo-orchestrator/agents`
- `exclusive`: `todo-orchestrator/references`
- `exclusive`: `todo-orchestrator/tests/test_workflow_front_door.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/config.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/front_door.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/service.py`
- `exclusive`: `workflow-unification/README.md`
- `read`: `workflow-unification/contracts`

## Dependencies
- `task`: `WFU-20`
<!-- todo-orchestrator:v2-managed:end -->
