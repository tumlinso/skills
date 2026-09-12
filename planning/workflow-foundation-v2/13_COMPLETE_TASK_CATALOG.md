# 13. Complete task catalog

This reading copy is generated from the authored catalog; current execution state lives only in the native authority.

# SK-WF2-COORD — Coordinate the accepted program; close only after final local integration

**Status: proposed, not implemented.** Native role: `coordinator`. Profile: `{"context_depth": "cross_project", "difficulty": "hard", "risk": "critical", "work_type": "architecture"}`.

## Purpose and mechanism

Hold a claimable ordinary coordinator seat and direct first-class lanes under the single strategic controller. Revalidate source, claims, receipts and resource limits. Continue coordinating while leaves run; the completion gate requires final local integration, not a claim-time dependency.

## Inputs and ordering

No task prerequisite. Revalidate source and authority before claiming.
This is a terminal obligation, not a claim-time wait: SK-WF2-I90.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: none; coordination only.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-COORD-A01:** The final local integration task and its checkpoint are successfully complete.
2. **SK-WF2-COORD-A02:** Every required producer/consumer receipt is current and unresolved blockers are recorded.
3. **SK-WF2-COORD-A03:** Owned work and explicit limitations are handed off before the aggregate epic closes.

## Evidence and completion

Gate `SK-WF2-COORD-G` invokes the delivered runner. Evidence kind is `closure`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-0000 — Workflow Foundation v2 — skills aggregate

**Status: proposed, not implemented.** Native role: `coordinator`. Profile: `{"context_depth": "focused", "difficulty": "routine", "risk": "high", "work_type": "review"}`.

## Purpose and mechanism

Close the aggregate only after all local child tasks, including the ordinary coordinator, have completed successfully and final evidence is coherent. The existing native aggregate readiness rule provides the child-completion check; no prerequisite points from a child back to this epic.

## Inputs and ordering

No task prerequisite. Revalidate source and authority before claiming.
This is a terminal obligation, not a claim-time wait: SK-WF2-COORD, SK-WF2-A01, SK-WF2-A02, SK-WF2-A03, SK-WF2-X01, SK-WF2-X02, SK-WF2-X03, SK-WF2-C01, SK-WF2-C02, SK-WF2-C03, SK-WF2-C04, SK-WF2-C05, SK-WF2-W01, SK-WF2-W02, SK-WF2-W03, SK-WF2-W04, SK-WF2-D01, SK-WF2-D02, SK-WF2-D03, SK-WF2-D04, SK-WF2-V01, SK-WF2-V02, SK-WF2-V03, SK-WF2-V04, SK-WF2-I10, SK-WF2-I20, SK-WF2-I40, SK-WF2-I60, SK-WF2-I90.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: none; coordination only.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-0000-A01:** Every local child is successfully terminal.
2. **SK-WF2-0000-A02:** The final local milestone remains qualified and integrated.
3. **SK-WF2-0000-A03:** The paired program release identity and limitations are explicitly reported.

## Evidence and completion

Gate `SK-WF2-0000-G` invokes the delivered runner. Evidence kind is `closure`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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


# SK-WF2-A02 — Freeze donor fixtures and preserve deployment recovery

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Retain old package and test identities outside the new runtime path. Produce sanitized versioned fixtures from supported exports or disposable sample projects; never copy secrets or active capability tokens.

## Inputs and ordering

Prerequisites: `SK-WF2-A01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/baseline`, `tests/wf2_acceptance/a`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-A02-A01:** Baseline inventory counts and required tests are reproducible.
2. **SK-WF2-A02-A02:** No real Cellerator/GlassHelix database is modified.
3. **SK-WF2-A02-A03:** Old deployment and source remain recoverable.

## Evidence and completion

Gate `SK-WF2-A02-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-A03 — Map independent ctxpp and host execution contracts

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "deep", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Describe ctxpp read/query/refresh/rewrite operations and host runtime facade consumers. Record which source identities are content hashes versus metadata and which schedulers are local versus host-wide.

## Inputs and ordering

Prerequisites: `SK-WF2-A02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/baseline`, `tests/wf2_acceptance/a`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-A03-A01:** Ctxpp standalone contract does not require a workflow DB.
2. **SK-WF2-A03-A02:** Read-only query and expensive refresh are separate capabilities.
3. **SK-WF2-A03-A03:** CPU/RAM reservation scope is not misrepresented as host-wide.

## Evidence and completion

Gate `SK-WF2-A03-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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


# SK-WF2-X02 — Import the supported new runtime interface

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "inspection"}`.

## Purpose and mechanism

Verify WF2-RUNTIME from PC-WF2-I20 and available candidate facade before rewiring CUDA/local-worker callers.

## Inputs and ordering

Prerequisites: `SK-WF2-X01`.
External receipt edge: `WF2-RUNTIME`; verify fresh producer authority, not an asserted done flag.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/imports`, `tests/wf2_acceptance/x`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-X02-A01:** Candidate supported APIs are source/hash qualified.
2. **SK-WF2-X02-A02:** No implicit sys.path fallback reintroduces the donor kernel.
3. **SK-WF2-X02-A03:** Installed old runtime is still unchanged.

## Evidence and completion

Gate `SK-WF2-X02-G` invokes the delivered runner. Evidence kind is `cross_receipt`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-X03 — Import actual deployment qualification

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "inspection"}`.

## Purpose and mechanism

Verify WF2-DEPLOYED from PC-WF2-I50 after candidate acceptance and actual release promotion.

## Inputs and ordering

Prerequisites: `SK-WF2-I60`.
External receipt edge: `WF2-DEPLOYED`; verify fresh producer authority, not an asserted done flag.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `docs/workflow_foundation_v2/imports`, `tests/wf2_acceptance/x`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-X03-A01:** Fresh HTTP/stdio release identity is recorded.
2. **SK-WF2-X03-A02:** Older writers are fenced or quiesced.
3. **SK-WF2-X03-A03:** Rehearsal-only evidence cannot satisfy this import.

## Evidence and completion

Gate `SK-WF2-X03-G` invokes the delivered runner. Evidence kind is `cross_receipt`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-C01 — Expose read-only indexed ctxpp queries

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "deep", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Create a small stable query facade over existing query.sqlite/manifest, supporting exact symbol ID, qualified name, canonical range and typed graph edges. No scanning or publication is permitted by this operation.

## Inputs and ordering

Prerequisites: `SK-WF2-X01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C01-A01:** Missing/stale index gives explicit unavailable/partial status.
2. **SK-WF2-C01-A02:** Queries work without Todo or Project Control installed.
3. **SK-WF2-C01-A03:** JSONL fallback is bounded and declared.

## Evidence and completion

Gate `SK-WF2-C01-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c01.py` and the exact cases:

    WF2Acceptance.test_missing_stale_index_gives_explicit_unavailable_partial_status
    WF2Acceptance.test_queries_work_without_todo_or_project_control_installed
    WF2Acceptance.test_jsonl_fallback_is_bounded_and_declared

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-C02 — Remove opportunistic Todo imports from source identity

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "hard", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Replace sibling sys.path injection with an independently implemented/versioned identity contract or a genuinely small shared contract dependency. Record algorithm/version/domain and which files/configurations are covered.

## Inputs and ordering

Prerequisites: `SK-WF2-C01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C02-A01:** Standalone and integrated identities have explicit comparability rules.
2. **SK-WF2-C02-A02:** Fallback source identity satisfies packet-v2 schema.
3. **SK-WF2-C02-A03:** Changing an unrelated file vs relevant dependency has documented freshness effects.

## Evidence and completion

Gate `SK-WF2-C02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c02.py` and the exact cases:

    WF2Acceptance.test_standalone_and_integrated_identities_have_explicit_comparability_rules
    WF2Acceptance.test_fallback_source_identity_satisfies_packet_v2_schema
    WF2Acceptance.test_changing_an_unrelated_file_vs_relevant_dependency_has_documented_freshness_effects

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-C03 — Strengthen packet schemas and trust accounting

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Validate nested task/context/trust/identity objects, not only top-level keys. Preserve whole canonical targets, explicit omissions and honest sufficiency when budget is too small or semantic relationships incomplete.

## Inputs and ordering

Prerequisites: `SK-WF2-C02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C03-A01:** Malformed nested identities/trust are rejected.
2. **SK-WF2-C03-A02:** Required canonical target is not silently truncated.
3. **SK-WF2-C03-A03:** Trust never calls lexical evidence semantic proof.

## Evidence and completion

Gate `SK-WF2-C03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c03.py` and the exact cases:

    WF2Acceptance.test_malformed_nested_identities_trust_are_rejected
    WF2Acceptance.test_required_canonical_target_is_not_silently_truncated
    WF2Acceptance.test_trust_never_calls_lexical_evidence_semantic_proof

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-C04 — Harden query publication and resource bounds

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "hard", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Test manifest/query-generation consistency under readers and publication. Document invocation-local CPU/RAM reservations; consume optional host admission without coupling standalone queries to workflow ownership.

## Inputs and ordering

Prerequisites: `SK-WF2-C03`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C04-A01:** Read-only readers cannot mutate the index.
2. **SK-WF2-C04-A02:** Interrupted publication produces explicit mismatch, not stale-current data.
3. **SK-WF2-C04-A03:** Concurrent expensive invocations respect the declared coordination domain.

## Evidence and completion

Gate `SK-WF2-C04-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c04.py` and the exact cases:

    WF2Acceptance.test_read_only_readers_cannot_mutate_the_index
    WF2Acceptance.test_interrupted_publication_produces_explicit_mismatch_not_stale_current_data
    WF2Acceptance.test_concurrent_expensive_invocations_respect_the_declared_coordination_domain

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-C05 — Qualify independent consumers and publish the ctxpp API

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Run standalone C++ fixture and Project Control adapter contract tests with semantic and lexical fallback scenarios. Preserve optional LibTooling limitations as explicit, not claims of a production-equivalent backend.

## Inputs and ordering

Prerequisites: `SK-WF2-C04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cpp-context-compiler/scripts`, `cpp-context-compiler/schemas`, `cpp-context-compiler/references`, `cpp-context-compiler/tests`, `tests/wf2_acceptance/c`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-C05-A01:** Real packet/query output validates against the contract.
2. **SK-WF2-C05-A02:** No installed Todo dependency remains.
3. **SK-WF2-C05-A03:** Source transform operations retain separate explicit authority and proof gates.

## Evidence and completion

Gate `SK-WF2-C05-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/c/test_sk_wf2_c05.py` and the exact cases:

    WF2Acceptance.test_real_packet_query_output_validates_against_the_contract
    WF2Acceptance.test_no_installed_todo_dependency_remains
    WF2Acceptance.test_source_transform_operations_retain_separate_explicit_authority_and_proof_gates

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-W01 — Construct forwarding-only legacy entry points

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "deep", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

After importing the supported new runtime, replace candidate old entry points with explicit forwards for documented imports, CLI and workflow protocol. Preserve old release outside the candidate for rollback/differential use.

## Inputs and ordering

Prerequisites: `SK-WF2-X02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `todo-orchestrator`, `integrations/coding-workflow-mcp`, `tests/wf2_acceptance/w`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-W01-A01:** Forwarded old/new symbols share one implementation.
2. **SK-WF2-W01-A02:** No fallback executes a second workflow kernel.
3. **SK-WF2-W01-A03:** Unsupported legacy paths report a clear migration error.

## Evidence and completion

Gate `SK-WF2-W01-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/w/test_sk_wf2_w01.py` and the exact cases:

    WF2Acceptance.test_forwarded_old_new_symbols_share_one_implementation
    WF2Acceptance.test_no_fallback_executes_a_second_workflow_kernel
    WF2Acceptance.test_unsupported_legacy_paths_report_a_clear_migration_error

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-W02 — Qualify legacy import and command behavior

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Test historical todo scripts, coding-workflow alias and runtime facades against the new installed product in isolated processes. Verify documented deprecation output and error codes without duplicate live MCP registration.

## Inputs and ordering

Prerequisites: `SK-WF2-W01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `todo-orchestrator`, `integrations/coding-workflow-mcp`, `tests/wf2_acceptance/w`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-W02-A01:** One authoritative DB/revision remains visible.
2. **SK-WF2-W02-A02:** Historical commands cannot bypass canonical write policy.
3. **SK-WF2-W02-A03:** Cross-package import cycles and import-order class identity bugs are rejected.

## Evidence and completion

Gate `SK-WF2-W02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/w/test_sk_wf2_w02.py` and the exact cases:

    WF2Acceptance.test_one_authoritative_db_revision_remains_visible
    WF2Acceptance.test_historical_commands_cannot_bypass_canonical_write_policy
    WF2Acceptance.test_cross_package_import_cycles_and_import_order_class_identity_bugs_are_rejected

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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


# SK-WF2-D01 — Route source and artifact consumers through supported contracts

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "cross_project", "difficulty": "complex", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Update enumerated CUDA/local-worker imports to the qualified facade or independent source contract. Keep command, source, artifact and evidence schemas stable unless explicitly versioned.

## Inputs and ordering

Prerequisites: `SK-WF2-X02`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cuda/scripts`, `cuda/tests`, `local-coding-worker/local_worker`, `local-coding-worker/scripts`, `local-coding-worker/tests`, `tests/wf2_acceptance/d`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-D01-A01:** Every inventoried consumer has a replacement mapping.
2. **SK-WF2-D01-A02:** No private sqlite/table dependency is introduced.
3. **SK-WF2-D01-A03:** Real candidate import tests pass.

## Evidence and completion

Gate `SK-WF2-D01-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/d/test_sk_wf2_d01.py` and the exact cases:

    WF2Acceptance.test_every_inventoried_consumer_has_a_replacement_mapping
    WF2Acceptance.test_no_private_sqlite_table_dependency_is_introduced
    WF2Acceptance.test_real_candidate_import_tests_pass

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-D02 — Preserve host-wide admission and lease behavior

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "hard", "risk": "high", "work_type": "implementation"}`.

## Purpose and mechanism

Rewire host coordinator access without creating a second host resource authority. Verify CPU/RAM/GPU request semantics, preemption, quiescence, PID incarnation and release on failures.

## Inputs and ordering

Prerequisites: `SK-WF2-D01`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cuda/scripts`, `cuda/tests`, `local-coding-worker/local_worker`, `local-coding-worker/scripts`, `local-coding-worker/tests`, `tests/wf2_acceptance/d`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-D02-A01:** Existing lease arbitration remains singular.
2. **SK-WF2-D02-A02:** Standalone engine behavior is explicitly supported or bounded.
3. **SK-WF2-D02-A03:** No helper resource request grants workflow permissions.

## Evidence and completion

Gate `SK-WF2-D02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/d/test_sk_wf2_d02.py` and the exact cases:

    WF2Acceptance.test_existing_lease_arbitration_remains_singular
    WF2Acceptance.test_standalone_engine_behavior_is_explicitly_supported_or_bounded
    WF2Acceptance.test_no_helper_resource_request_grants_workflow_permissions

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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


# SK-WF2-D04 — Qualify consumers and resource failure paths

**Status: proposed, not implemented.** Native role: `implementer`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Execute representative CUDA-controller orchestration and local-worker contract tests on isolated fixtures; run actual hardware tests only where declared and available. Record hardware-unavailable as blocked for those assertions.

## Inputs and ordering

Prerequisites: `SK-WF2-D03`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `cuda/scripts`, `cuda/tests`, `local-coding-worker/local_worker`, `local-coding-worker/scripts`, `local-coding-worker/tests`, `tests/wf2_acceptance/d`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-D04-A01:** Mocked lease tests are not reported as actual GPU execution.
2. **SK-WF2-D04-A02:** Consumer inventory coverage is complete.
3. **SK-WF2-D04-A03:** Current source/build/runtime identities accompany test results.

## Evidence and completion

Gate `SK-WF2-D04-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/d/test_sk_wf2_d04.py` and the exact cases:

    WF2Acceptance.test_mocked_lease_tests_are_not_reported_as_actual_gpu_execution
    WF2Acceptance.test_consumer_inventory_coverage_is_complete
    WF2Acceptance.test_current_source_build_runtime_identities_accompany_test_results

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-V01 — Review donor mapping and parity evidence independently

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "review"}`.

## Purpose and mechanism

Check module/test inventory, sensitive-state exclusions, baseline release retention and replacement paths against the actual donor tree.

## Inputs and ordering

Prerequisites: `SK-WF2-A03`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V01-A01:** No module disappears without an explicit disposition.
2. **SK-WF2-V01-A02:** No authority tokens or runtime DB enter the package.
3. **SK-WF2-V01-A03:** Donor map supports independent reproduction.

## Evidence and completion

Gate `SK-WF2-V01-G` invokes the delivered runner. Evidence kind is `governance`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-V02 — Test ctxpp with no workflow products installed

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "testing"}`.

## Purpose and mechanism

Install/run the bounded query/packet contract in a clean isolated environment with a real C++ fixture. Include stale manifest, missing index, unsupported backend, tiny budget and changed source cases.

## Inputs and ordering

Prerequisites: `SK-WF2-C05`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V02-A01:** Standalone operation never imports project_control or todo_orchestrator.
2. **SK-WF2-V02-A02:** All mandatory schema/trust cases execute with zero skips.
3. **SK-WF2-V02-A03:** Read query leaves canonical source and .ctxpp bytes unchanged.

## Evidence and completion

Gate `SK-WF2-V02-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/v/test_sk_wf2_v02.py` and the exact cases:

    WF2Acceptance.test_standalone_operation_never_imports_project_control_or_todo_orchestrator
    WF2Acceptance.test_all_mandatory_schema_trust_cases_execute_with_zero_skips
    WF2Acceptance.test_read_query_leaves_canonical_source_and_ctxpp_bytes_unchanged

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


# SK-WF2-V03 — Test forwarding shims and real consumer boundaries

**Status: proposed, not implemented.** Native role: `specialist`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "critical", "work_type": "testing"}`.

## Purpose and mechanism

Independently exercise W/D candidate from both historical entry points and new supported APIs, including process crashes and incompatible runtime identity.

## Inputs and ordering

Prerequisites: `SK-WF2-W04`, `SK-WF2-D04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `tests/wf2_validation`, `docs/workflow_foundation_v2/validation`, `tests/wf2_acceptance/v`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-V03-A01:** One implementation services old and new calls.
2. **SK-WF2-V03-A02:** Mixed unsafe versions fail closed.
3. **SK-WF2-V03-A03:** No skipped mandatory consumer scenario.

## Evidence and completion

Gate `SK-WF2-V03-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/v/test_sk_wf2_v03.py` and the exact cases:

    WF2Acceptance.test_one_implementation_services_old_and_new_calls
    WF2Acceptance.test_mixed_unsafe_versions_fail_closed
    WF2Acceptance.test_no_skipped_mandatory_consumer_scenario

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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


# SK-WF2-I40 — Integrate forwarding shims and engine consumers

**Status: proposed, not implemented.** Native role: `integrator`. Profile: `{"context_depth": "focused", "difficulty": "complex", "risk": "high", "work_type": "integration"}`.

## Purpose and mechanism

Integrate W/D changes with the exact recipient candidate. Check root registration/docs so only Project Control is the normal workflow product.

## Inputs and ordering

Prerequisites: `SK-WF2-I20`, `SK-WF2-W04`, `SK-WF2-D04`.

Preceding tasks in the same lane also impose serial order. A producer being done is insufficient if its qualified source is absent from this worktree. See `09_PARALLELISM_AND_INTEGRATION.md`.

## Source ownership

Write scope: `pyproject.toml`, `README.md`, `AGENTS.md`, `docs/workflow_foundation_v2/integration`, `tests/wf2_acceptance/i`.

Read the sealed package and exact source ledger references. New source/test paths in this plan are **proposed**, not claims that files already exist. Source scope changes require the actual authoritative workflow; never bypass a denied operation with direct SQL.

## Acceptance

1. **SK-WF2-I40-A01:** Alias compatibility is not a second live product.
2. **SK-WF2-I40-A02:** No donor private imports remain in maintained consumers.
3. **SK-WF2-I40-A03:** New runtime contracts match the PC receipt.

## Evidence and completion

Gate `SK-WF2-I40-G` invokes the delivered runner. Evidence kind is `tests`. No acceptance record is shipped as passed. The runner reads an explicit external `WF2_BINDINGS` file.

Implement the acceptance file `tests/wf2_acceptance/i/test_sk_wf2_i40.py` and the exact cases:

    WF2Acceptance.test_alias_compatibility_is_not_a_second_live_product
    WF2Acceptance.test_no_donor_private_imports_remain_in_maintained_consumers
    WF2Acceptance.test_new_runtime_contracts_match_the_pc_receipt

These are proposed test names, not existing tests or empty stubs. They must execute meaningful assertions against real code and include the corresponding negative controls. Additional existing regression suites are required by the task mechanism and review record. Zero tests, skipped cases and expected-failure substitutions fail qualification.

Commit source under test, run the gate, and place review/evidence outside repository roots. Each assertion must cite hashed evidence. An independent reviewer checks the substance; JSON shape alone does not prove correctness. Publish owned interfaces before completion where required. Preserve negative results and report external blockers honestly.

## Delegation and autonomy

After the user launches the controller, execute within this task and the accepted scope without asking for every engineering choice. Prefer the configured inexpensive worker; request a bounded read-only researcher for deep archaeology and a capable independent reviewer for consequential claims. Keep model settings outside task semantics. Do not load the full catalog into every worker; use this sheet, its producers and relevant source only. See `07_CODEX_AGENT_ROUTING.md` and the lane handoff.


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
