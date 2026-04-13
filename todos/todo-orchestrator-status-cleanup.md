# Current Objective

## Summary
Extend todo-orchestrator with a pickup-aware `todo-status.md`, explicit `todo-cleanup`, and additive quick-start guidance for fresh threads.

## Quick Start
- Why this stream exists: Add pickup coordination and explicit cleanup without replacing the existing todo-orchestrator ledger model.
- In scope: Shared helper updates, todo-status synchronization, cleanup script, docs, tests, and current-ledger synchronization.
- Out of scope / dependencies: Do not replace planned/in_progress/blocked/done; keep existing helper script entrypoints compatible.
- Required skills: `todo-orchestrator`, `skill-creator`.
- Required references: `todo-orchestrator/references/todo-format.md`, `todo-orchestrator/references/planning-workflow.md`, `todo-orchestrator/references/status-and-cleanup.md`.

## Planning Notes
_None recorded yet._

## Assumptions
_None recorded yet._

## Suggested Skills
- `todo-orchestrator` - Primary skill being extended and validated.
- `skill-creator` - Keep the skill concise while adding the new workflow surface.

## Useful Reference Files
- `todo-orchestrator/references/todo-format.md` - Canonical ledger and pickup-register layout.
- `todo-orchestrator/references/status-and-cleanup.md` - Claiming rules and explicit cleanup policy.

## Plan
- Extend shared helpers to manage `todo-status.md`, quick-start blocks, claim states, and cleanup readiness.
- Update helper scripts and skill docs to expose pickup-aware execution and explicit cleanup.
- Add tests covering pickup-ready vs claimed streams, compatibility, and cleanup gating.

## Tasks
- [x] Extend todo_common.py for todo-status support
- [x] Update helper scripts and skill docs
- [x] Add validation coverage for pickup and cleanup flows

## Blockers
_None recorded yet._

## Progress Notes
- Implemented additive pickup tracking, cleanup helpers, and quick-start requirements for exact required skills and references.
- Validated the extension with the todo-orchestrator unit tests, script compilation, and frontmatter/UI metadata checks.
- Hardened `update_todos.py` with a JSON `--payload-file` path so ledger updates can preserve backticks, globs, and markdown-heavy repro text without shell expansion.
- Clarified the serial execution rules so unclaimed `ready` or `idle` workstreams must be picked up immediately instead of waiting or asking the user what to do next.

## Next Actions
- Run skill-level validation and sync the repo ledgers to the new format.
- Implementation is complete; call `todo-cleanup` only if explicit cleanup is requested.
- Resume only if more todo-orchestrator script hardening is needed.
- Resume only if more todo-orchestrator execution wording needs tightening.

## Done Criteria
- todo-orchestrator tracks pickup-ready versus claimed work without replacing the existing workstream status model.
- todo-cleanup stays explicit and only succeeds when every tracked workstream is done.
