

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-06: Add task-oriented cpp-context packets and one inspect front door

Task revision: `62`; current project revision is in `todo-status.md`.

## Objective
Add a machine-oriented ctxpp packet command and an ordinary inspect command that select exact canonical edit targets plus compact types, dependencies, callers/callees, tests, invariants, source locations, trust metadata, hashes, and bounded expansion handles.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `parallel_safe`
- Result: `implemented`

## Next Action
Implement additive inspect/packet commands without weakening fast where/route/status behavior or source-authority guarantees.

## Ownership
- `exclusive`: `cpp-context-compiler/references/context-packets.md`
- `exclusive`: `cpp-context-compiler/schemas/context-packet-v1.schema.json`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_lib.py`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_packet.py`
- `exclusive`: `cpp-context-compiler/tests/test_context_packet.py`
- `read`: `contracts/source-identity-v1.schema.json`
- `read`: `cpp-context-compiler/scripts/ctxpp_fast.py`
- `read`: `cpp-context-compiler/tests/fixtures`

## Dependencies
- `checkpoint`: `CORE4-RUNTIME-FROZEN`
- `checkpoint`: `CORE4-BASELINE-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
