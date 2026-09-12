# SK-WF2-A01 — Inventory Todo donor source and public consumers

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "deep", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Capture all todo_orchestrator modules, tests, scripts, supported imports, package entry points and runtime sidecars at the reviewed Skills commit. Audit CUDA, local-worker and ctxpp imports by exact paths.

## Inputs and ordering

No task prerequisite. Revalidate source and authority before claiming.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/baseline`, `tests/wf2_acceptance/a`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-A01-A01:** Complete source/test inventory hashes are available.
2. **SK-WF2-A01-A02:** Unknown external consumers are recorded as compatibility risks.
3. **SK-WF2-A01-A03:** No live Todo data is included in export.

## Evidence and completion

Gate `SK-WF2-A01-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
