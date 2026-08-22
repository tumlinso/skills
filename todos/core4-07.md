

<!-- todo-orchestrator:v2-managed:start -->
# CORE4-07: Instrument ctxpp consumer economics and worker packet evaluation

Task revision: `23`; current project revision is in `todo-status.md`.

## Objective
Measure packet latency, freshness, exact versus compact tokens, canonical source avoided, expansions, broad source fallbacks, local-worker success, accepted patches, and Codex reinvestigation without adding routine output or a dashboard.

## State
- Lifecycle: `planned`
- Execution: `ready`
- Parallel policy: `serial`
- Result: `-`

## Next Action
Add private bounded telemetry and a fixture evaluation that compares packet layouts at fixed budgets. Do not optimize solely for token reduction.

## Ownership
- `exclusive`: `cpp-context-compiler/evals`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_packet.py`
- `exclusive`: `cpp-context-compiler/scripts/ctxpp_telemetry.py`
- `exclusive`: `cpp-context-compiler/tests/expected/context-packet-economics.json`
- `exclusive`: `cpp-context-compiler/tests/test_context_packet_economics.py`
- `read`: `cpp-context-compiler/tests/fixtures`
- `read`: `local-coding-worker`

## Dependencies
- `checkpoint`: `CORE4-CTXPP-PACKET-FROZEN`
<!-- todo-orchestrator:v2-managed:end -->
