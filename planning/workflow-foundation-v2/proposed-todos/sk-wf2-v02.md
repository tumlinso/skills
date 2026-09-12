# SK-WF2-V02 — Test ctxpp with no workflow products installed

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Install/run the bounded query/packet contract in a clean isolated environment with a real C++ fixture. Include stale manifest, missing index, unsupported backend, tiny budget and changed source cases.

## Inputs and ordering

Prerequisites: `SK-WF2-C05`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V02-A01:** Standalone operation never imports project_control or todo_orchestrator.
2. **SK-WF2-V02-A02:** All mandatory schema/trust cases execute with zero skips.
3. **SK-WF2-V02-A03:** Read query leaves canonical source and .ctxpp bytes unchanged.

## Evidence and completion

Gate `SK-WF2-V02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/v/test_sk_wf2_v02.py` and the exact cases:

    WF2Acceptance.test_standalone_operation_never_imports_project_control_or_todo_orchestrator
    WF2Acceptance.test_all_mandatory_schema_trust_cases_execute_with_zero_skips
    WF2Acceptance.test_read_query_leaves_canonical_source_and_ctxpp_bytes_unchanged

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
