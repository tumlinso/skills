# SK-WF2-W04 — Publish support-window and final removal criteria

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Document supported legacy calls, compatibility tests, expiry criteria and later optional total shim removal. Do not force removal of externally used entry points without an inventory.

## Inputs and ordering

Prerequisites: `SK-WF2-W03`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `todo-orchestrator`, `integrations/coding-workflow-mcp`, `tests/wf2_acceptance/w`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-W04-A01:** Compatibility is temporary and has measurable exit criteria.
2. **SK-WF2-W04-A02:** No active deployment is silently broken.
3. **SK-WF2-W04-A03:** State directory migration is explicitly deferred.

## Evidence and completion

Gate `SK-WF2-W04-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
