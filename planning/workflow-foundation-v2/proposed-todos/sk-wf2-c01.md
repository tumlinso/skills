# SK-WF2-C01 — Expose read-only indexed ctxpp queries

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "deep", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Create a small stable query facade over existing query.sqlite/manifest, supporting exact symbol ID, qualified name, canonical range and typed graph edges. No scanning or publication is permitted by this operation.

## Inputs and ordering

Prerequisites: `SK-WF2-X01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C01-A01:** Missing/stale index gives explicit unavailable/partial status.
2. **SK-WF2-C01-A02:** Queries work without Todo or Project Control installed.
3. **SK-WF2-C01-A03:** JSONL fallback is bounded and declared.

## Evidence and completion

Gate `SK-WF2-C01-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c01.py` and the exact cases:

    WF2Acceptance.test_missing_stale_index_gives_explicit_unavailable_partial_status
    WF2Acceptance.test_queries_work_without_todo_or_project_control_installed
    WF2Acceptance.test_jsonl_fallback_is_bounded_and_declared

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
