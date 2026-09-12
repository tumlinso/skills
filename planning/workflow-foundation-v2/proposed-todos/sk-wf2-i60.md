# SK-WF2-I60 — Publish consumer-ready paired release acceptance

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "integration"}`.

## Purpose and mechanism

Integrate independent V03 checks and publish WF2-CONSUMERS. This milestone precedes actual PC deployment and does not wait for PC final closure.

## Inputs and ordering

Prerequisites: `SK-WF2-I40`, `SK-WF2-V03`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I60-A01:** All required shim/ctxpp/consumer tests pass.
2. **SK-WF2-I60-A02:** Candidate source pair and build identities are fixed.
3. **SK-WF2-I60-A03:** Actual deployment remains a separate milestone.

## Evidence and completion

Gate `SK-WF2-I60-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/i/test_sk_wf2_i60.py` and the exact cases:

    WF2Acceptance.test_all_required_shim_ctxpp_consumer_tests_pass
    WF2Acceptance.test_candidate_source_pair_and_build_identities_are_fixed
    WF2Acceptance.test_actual_deployment_remains_a_separate_milestone

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
