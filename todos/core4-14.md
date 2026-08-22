

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-14: Integrate todo to ctxpp to local worker to acceptance to CUDA discovery

Task revision: `163`; current project revision is in `todo-status.md`.

## Objective
Build the complete fake-backend software flow: delegate by todo task identity, compile a bounded ctxpp packet, run a terminal local worker, externally verify, surface a compact result, guardedly accept a patch, and trigger relevant CUDA campaign discovery while healthy evidence remains silent.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `integration_exclusive`
- Result: `implemented`

## Next Action
Wire only stable interfaces. Do not bypass them with private imports. Prove read-only, writable, NEEDS_CODEX, stale patch, preemption, accepted patch, and CUDA-trigger cases.

## Ownership
- `exclusive`: `core4-tests/integration`
- `exclusive`: `local-coding-worker/local_worker/controller.py`
- `exclusive`: `local-coding-worker/references/integration-contract.md`
- `exclusive`: `local-coding-worker/scripts/local_worker.py`
- `exclusive`: `local-coding-worker/tests/test_core4_integration.py`
- `read`: `contracts`
- `read`: `cpp-context-compiler`
- `read`: `cuda`
- `read`: `todo-orchestrator`

## Dependencies
- `barrier`: `CORE4-LANES-READY`
<!-- todo-orchestrator:v2-managed:end -->
