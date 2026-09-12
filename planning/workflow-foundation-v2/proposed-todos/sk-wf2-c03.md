# SK-WF2-C03 — Strengthen packet schemas and trust accounting

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Validate nested task/context/trust/identity objects, not only top-level keys. Preserve whole canonical targets, explicit omissions and honest sufficiency when budget is too small or semantic relationships incomplete.

## Inputs and ordering

Prerequisites: `SK-WF2-C02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C03-A01:** Malformed nested identities/trust are rejected.
2. **SK-WF2-C03-A02:** Required canonical target is not silently truncated.
3. **SK-WF2-C03-A03:** Trust never calls lexical evidence semantic proof.

## Evidence and completion

Gate `SK-WF2-C03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c03.py` and the exact cases:

    WF2Acceptance.test_malformed_nested_identities_trust_are_rejected
    WF2Acceptance.test_required_canonical_target_is_not_silently_truncated
    WF2Acceptance.test_trust_never_calls_lexical_evidence_semantic_proof

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
