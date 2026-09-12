# SK-WF2-D03 — Preserve subordinate worker acceptance semantics

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "hard", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Verify bounded child scope, candidate vs accepted result, nonblocking collection and parent-only completion after rewiring. Distinguish first-class Codex workers from local execution children.

## Inputs and ordering

Prerequisites: `SK-WF2-D02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cuda/scripts`, `cuda/tests`, `local-coding-worker/local_worker`, `local-coding-worker/scripts`, `local-coding-worker/tests`, `tests/wf2_acceptance/d`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-D03-A01:** Child cannot publish parent completion or impersonate a lane.
2. **SK-WF2-D03-A02:** Unavailable local worker returns control without polling loops.
3. **SK-WF2-D03-A03:** Failed candidate retains logs/evidence without source loss.

## Evidence and completion

Gate `SK-WF2-D03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/d/test_sk_wf2_d03.py` and the exact cases:

    WF2Acceptance.test_child_cannot_publish_parent_completion_or_impersonate_a_lane
    WF2Acceptance.test_unavailable_local_worker_returns_control_without_polling_loops
    WF2Acceptance.test_failed_candidate_retains_logs_evidence_without_source_loss

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.
