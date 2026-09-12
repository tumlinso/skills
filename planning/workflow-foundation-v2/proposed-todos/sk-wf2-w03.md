# SK-WF2-W03 — Remove the maintained duplicate kernel from the new path

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "integration"}`.

## Purpose and mechanism

Retire copied implementation only after parity and legacy conformance. Keep immutable historical source via Git/tags/artifacts; update packaging so the released shim depends on the accepted PC artifact, never an unpinned mutable checkout.

## Inputs and ordering

Prerequisites: `SK-WF2-W02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `todo-orchestrator`, `integrations/coding-workflow-mcp`, `tests/wf2_acceptance/w`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-W03-A01:** Skills contains only declared forwarding compatibility for Todo.
2. **SK-WF2-W03-A02:** Old baseline remains reproducible outside production.
3. **SK-WF2-W03-A03:** No installation still requires sibling Todo discovery for the new product.

## Evidence and completion

Gate `SK-WF2-W03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/w/test_sk_wf2_w03.py` and the exact cases:

    WF2Acceptance.test_skills_contains_only_declared_forwarding_compatibility_for_todo
    WF2Acceptance.test_old_baseline_remains_reproducible_outside_production
    WF2Acceptance.test_no_installation_still_requires_sibling_todo_discovery_for_the_new_product

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
