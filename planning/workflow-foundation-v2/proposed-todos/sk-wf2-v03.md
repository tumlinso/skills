# SK-WF2-V03 — Test forwarding shims and real consumer boundaries

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "critical", "work_type": "testing"}`.

## Purpose and mechanism

Independently exercise W/D candidate from both historical entry points and new supported APIs, including process crashes and incompatible runtime identity.

## Inputs and ordering

Prerequisites: `SK-WF2-W04`, `SK-WF2-D04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V03-A01:** One implementation services old and new calls.
2. **SK-WF2-V03-A02:** Mixed unsafe versions fail closed.
3. **SK-WF2-V03-A03:** No skipped mandatory consumer scenario.

## Evidence and completion

Gate `SK-WF2-V03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/v/test_sk_wf2_v03.py` and the exact cases:

    WF2Acceptance.test_one_implementation_services_old_and_new_calls
    WF2Acceptance.test_mixed_unsafe_versions_fail_closed
    WF2Acceptance.test_no_skipped_mandatory_consumer_scenario

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
