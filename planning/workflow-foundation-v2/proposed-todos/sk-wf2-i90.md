# SK-WF2-I90 — Close Skills work after qualified deployment

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

After V04, verify final main integration, published compatibility obligations and retained historical baseline. Publish WF2-SK-FINAL; COORD and root epic close afterward.

## Inputs and ordering

Prerequisites: `SK-WF2-I60`, `SK-WF2-V04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I90-A01:** All Skills-owned work is integrated and qualified.
2. **SK-WF2-I90-A02:** No unrelated worktree or older program is cleaned.
3. **SK-WF2-I90-A03:** Final receipt enables PC closure without waiting on its final epic.

## Evidence and completion

Gate `SK-WF2-I90-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
