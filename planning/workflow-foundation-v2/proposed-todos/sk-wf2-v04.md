# SK-WF2-V04 — Verify final migration after the release switch

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "review"}`.

## Purpose and mechanism

After actual deployed receipt, run bounded read/import smoke with new release and observe old-entry compatibility without mutating unrelated authorities. Verify retained rollback and source closure.

## Inputs and ordering

Prerequisites: `SK-WF2-X03`, `SK-WF2-I60`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V04-A01:** Actual deployed identity matches accepted candidate.
2. **SK-WF2-V04-A02:** Real existing project UUIDs are preserved.
3. **SK-WF2-V04-A03:** Known limitations remain explicit.

## Evidence and completion

Gate `SK-WF2-V04-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
