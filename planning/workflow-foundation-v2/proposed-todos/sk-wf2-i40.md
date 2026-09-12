# SK-WF2-I40 — Integrate forwarding shims and engine consumers

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "integration"}`.

## Purpose and mechanism

Integrate W/D changes with the exact recipient candidate. Check root registration/docs so only Project Control is the normal workflow product.

## Inputs and ordering

Prerequisites: `SK-WF2-I20`, `SK-WF2-W04`, `SK-WF2-D04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I40-A01:** Alias compatibility is not a second live product.
2. **SK-WF2-I40-A02:** No donor private imports remain in maintained consumers.
3. **SK-WF2-I40-A03:** New runtime contracts match the PC receipt.

## Evidence and completion

Gate `SK-WF2-I40-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/i/test_sk_wf2_i40.py` and the exact cases:

    WF2Acceptance.test_alias_compatibility_is_not_a_second_live_product
    WF2Acceptance.test_no_donor_private_imports_remain_in_maintained_consumers
    WF2Acceptance.test_new_runtime_contracts_match_the_pc_receipt

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
