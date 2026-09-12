# SK-WF2-C02 — Remove opportunistic Todo imports from source identity

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "hard", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Replace sibling sys.path injection with an independently implemented/versioned identity contract or a genuinely small shared contract dependency. Record algorithm/version/domain and which files/configurations are covered.

## Inputs and ordering

Prerequisites: `SK-WF2-C01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C02-A01:** Standalone and integrated identities have explicit comparability rules.
2. **SK-WF2-C02-A02:** Fallback source identity satisfies packet-v2 schema.
3. **SK-WF2-C02-A03:** Changing an unrelated file vs relevant dependency has documented freshness effects.

## Evidence and completion

Gate `SK-WF2-C02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c02.py` and the exact cases:

    WF2Acceptance.test_standalone_and_integrated_identities_have_explicit_comparability_rules
    WF2Acceptance.test_fallback_source_identity_satisfies_packet_v2_schema
    WF2Acceptance.test_changing_an_unrelated_file_vs_relevant_dependency_has_documented_freshness_effects

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
