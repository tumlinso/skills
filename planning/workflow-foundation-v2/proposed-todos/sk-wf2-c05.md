# SK-WF2-C05 — Qualify independent consumers and publish the ctxpp API

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Run standalone C++ fixture and Project Control adapter contract tests with semantic and lexical fallback scenarios. Preserve optional LibTooling limitations as explicit, not claims of a production-equivalent backend.

## Inputs and ordering

Prerequisites: `SK-WF2-C04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C05-A01:** Real packet/query output validates against the contract.
2. **SK-WF2-C05-A02:** No installed Todo dependency remains.
3. **SK-WF2-C05-A03:** Source transform operations retain separate explicit authority and proof gates.

## Evidence and completion

Gate `SK-WF2-C05-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c05.py` and the exact cases:

    WF2Acceptance.test_real_packet_query_output_validates_against_the_contract
    WF2Acceptance.test_no_installed_todo_dependency_remains
    WF2Acceptance.test_source_transform_operations_retain_separate_explicit_authority_and_proof_gates

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
