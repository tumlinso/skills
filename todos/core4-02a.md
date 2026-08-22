

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-02A: Resolve ctxpp targeted-refresh baseline contract

Task revision: `140`; current project revision is in `todo-status.md`.

## Objective
Determine whether a newly populated included header may be served by the lexical-overlay fast path or must trigger one semantic TU refresh, then make the smallest backwards-compatible implementation or test correction and restore the ctxpp baseline.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Inspect the targeted refresh implementation, failing test, and existing ctxpp retrieval/freshness contract; change only the test if lexical-only freshness is contract-valid, otherwise repair the implementation; run the focused test and full ctxpp suite, then freeze CORE4-BASELINE-FROZEN.

## Ownership
- `exclusive`: `contracts/core4-compatibility-v1.json`
- `exclusive`: `core4-tests/baseline/README.md`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_fast.py`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_lib.py`
- `exclusive`: `cpp-context-compiler/tests/test_integration.py`
- `read`: `cpp-context-compiler/SKILL.md`
- `read`: `cpp-context-compiler/references`
- `read`: `cpp-context-compiler/tests/expected`

## Dependencies
- `task`: `CORE4-01`
<!-- todo-orchestrator:v2-managed:end -->
