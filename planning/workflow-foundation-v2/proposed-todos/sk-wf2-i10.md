# SK-WF2-I10 — Publish the donor baseline and test inventory

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Integrate A/V01 records and publish WF2-DONOR with full source/test dependency identity. No maintained donor code is removed in this milestone.

## Inputs and ordering

Prerequisites: `SK-WF2-A03`, `SK-WF2-V01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I10-A01:** Donor inventory is complete and reproducible.
2. **SK-WF2-I10-A02:** Producer completion is visible in the Skills authority.
3. **SK-WF2-I10-A03:** Receipt does not contain a self-referential commit hash.

## Evidence and completion

Gate `SK-WF2-I10-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
