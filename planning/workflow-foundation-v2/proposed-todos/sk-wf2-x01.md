# SK-WF2-X01 — Import Project Control parity approval

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "inspection"}`.

## Purpose and mechanism

Verify WF2-PARITY and fresh PC-WF2-I10 completion before changing consumers or deleting donor implementation.

## Inputs and ordering

Prerequisites: `SK-WF2-A03`.
External receipt edge: `WF2-PARITY`; verify fresh producer authority, not an asserted done flag.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/imports`, `tests/wf2_acceptance/x`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-X01-A01:** Qualified old/new source and tests are identified.
2. **SK-WF2-X01-A02:** No semantic refactor begins before parity.
3. **SK-WF2-X01-A03:** Receipt uses the actual PC UUID.

## Evidence and completion

Gate `SK-WF2-X01-G` invokes the delivered runner. Evidence kind is `cross_receipt`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
