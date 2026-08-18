---
slug: "cpp-context-compiler"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-08-17T14:17:58Z"
last_heartbeat_at: "2026-08-17T15:08:40Z"
last_reviewed_at: "2026-08-17T14:17:58Z"
stale_after_days: 3
objective: "Implement and validate a complete V1 cpp-context-compiler Codex skill and local Clang-based toolkit"
---

# Current Objective

## Summary
Build the new standalone skill without modifying unrelated user-owned work.

## Quick Start
- Why this stream exists: deliver a working context compiler for C++ retrieval, compact views, safe sharding, and conservative source plans.
- In scope: new cpp-context-compiler directory, concise routed skill docs, Clang semantic core, deterministic wrapper/tooling, tests, fixtures, and evals.
- Out of scope: package installation, network services, implicit canonical rewrites, edits to unrelated skills.
- Required skills: skill-creator and todo-orchestrator.
- Required references: skill-creator SKILL.md and openai_yaml.md; todo-orchestrator planning-workflow.md and todo-format.md.

## Planning Notes
- Prioritize semantic indexing and slicing; expose degraded routing when local Clang development headers are unavailable.
- Keep generated views read-only and require explicit apply for canonical source mutation.

## Assumptions
- Use the repository root as the requested parent and create cpp-context-compiler/.
- Use Python only for orchestration, stable JSONL, token adapters, transactions, and tests; keep semantic extraction and rewrite decisions in C++/Clang.
- Use Unix Makefiles because Ninja is unavailable.

## Suggested Skills
- `skill-creator` - Create and validate the standalone skill package.
- `todo-orchestrator` - Maintain a resumable implementation ledger.

## Useful Reference Files
- `/home/tumlinson/.codex/skills/.system/skill-creator/SKILL.md` - Skill structure and validation workflow.
- `todo-orchestrator/references/planning-workflow.md` - Multi-step execution planning.
- `todo-orchestrator/references/todo-format.md` - Ledger schema.

## Plan
- Initialize the skill through init_skill.py and author conditional references and assets.
- Implement a buildable Clang LibTooling semantic indexer and deterministic ctxpp wrapper.
- Implement routing, slicing, compact views, audit/lint, plans, transaction/rollback, and same-TU sharding.
- Add semantic fixtures, integration tests, and a compact Codex utility eval harness.
- Build, test, forward-test independently, address failures, and record evidence.

## Tasks
- [x] Inspect environment and initialize skill
- [x] Implement docs and configuration
- [x] Implement semantic core and wrapper
- [x] Implement tests and evals
- [x] Validate and forward-test
- [x] Finalize evidence and limitations

## Blockers
_None recorded yet._

## Progress Notes
- Implemented the complete cpp-context-compiler V1 with a dynamic libclang semantic index, optional LibTooling target, incremental JSONL records, deterministic routing/slicing/views, safe plans, transactions, rollback, sharding, linting, tests, and evals.
- Validated 17 integration and unit tests, the CMake core smoke test, skill metadata, a 14-prompt eval with 47.63 percent median context reduction and zero implicit mutations, and byte-exact reversal for rename and sharding plans.
- Independent retrieval and mutation forward-tests exposed and drove fixes for macro/nonlocal-state routing, rename accounting, sharding slice cost, and verification tier enforcement.

## Next Actions
- No immediate action; use the skill on an opted-in C++ repository and extend conservative rules only with fixtures and proof-level verification.

## Done Criteria
- Skill metadata validates and routes only opt-in or explicit C++ context-reduction requests.
- Opted-in fixture scans, resolves symbols, slices within budgets, and maps compact views to canonical source.
- Sharding and one conservative rewrite plan apply transactionally, verify, reverse, and roll back on failure.
- Tests and evals demonstrate deterministic outputs, context savings, correctness, protected names, and safe degraded behavior.
