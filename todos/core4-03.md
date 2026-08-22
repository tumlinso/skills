

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-03: Expose minimal shared runtime contracts and facade

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Define tiny cross-skill command, source-identity, resource-request, artifact-reference, and evidence-summary contracts; expose supported todo runtime facades for jobs, snapshots, artifacts, and host resources while preserving all existing private background compatibility.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Add schemas and thin adapters around current background primitives. Do not redesign the scheduler or move skill-specific semantics into the facade.

## Ownership
- `exclusive`: `contracts/artifact-ref-v1.schema.json`
- `exclusive`: `contracts/command-spec-v1.schema.json`
- `exclusive`: `contracts/evidence-summary-v1.schema.json`
- `exclusive`: `contracts/resource-request-v1.schema.json`
- `exclusive`: `contracts/source-identity-v1.schema.json`
- `exclusive`: `todo-orchestrator/tests/test_runtime_facade.py`
- `exclusive`: `todo-orchestrator/todo_orchestrator/runtime`
- `read`: `todo-orchestrator/tests/test_background_runtime.py`
- `read`: `todo-orchestrator/tests/test_host_coordination.py`
- `read`: `todo-orchestrator/todo_orchestrator/background`

## Dependencies
- `checkpoint`: `CORE4-BASELINE-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
