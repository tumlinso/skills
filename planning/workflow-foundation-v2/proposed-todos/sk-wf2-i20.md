# SK-WF2-I20 — Integrate and publish the standalone ctxpp contract

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "integration"}`.

## Purpose and mechanism

Integrate C05/V02 and publish WF2-CTXPP for the PC adapter. Keep independent CLI/config/state and separate refresh/rewrite authority.

## Inputs and ordering

Prerequisites: `SK-WF2-I10`, `SK-WF2-C05`, `SK-WF2-V02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I20-A01:** Standalone qualified query/packet contract is installed in candidate.
2. **SK-WF2-I20-A02:** No kernel code has moved into ctxpp.
3. **SK-WF2-I20-A03:** Receipt includes actual fixture execution.

## Evidence and completion

Gate `SK-WF2-I20-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/i/test_sk_wf2_i20.py` and the exact cases:

    WF2Acceptance.test_standalone_qualified_query_packet_contract_is_installed_in_candidate
    WF2Acceptance.test_no_kernel_code_has_moved_into_ctxpp
    WF2Acceptance.test_receipt_includes_actual_fixture_execution

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
