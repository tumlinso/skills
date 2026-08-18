---
slug: "deprecate-cuda-v100-by-routing-live-handoffs-to-cuda-and-leaving-only-a-compatibility-shim"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-17T18:46:51Z"
last_heartbeat_at: "2026-04-17T18:51:16Z"
last_reviewed_at: "2026-04-17T18:51:16Z"
stale_after_days: 14
objective: "Deprecate cuda-v100 by routing live skill handoffs to cuda and leaving only a compatibility shim."
---

# Current Objective

## Summary
Deprecate cuda-v100 by removing it as a live routing target, migrating active handoffs to cuda, and keeping only a marked compatibility shim.

## Quick Start
- Why this stream exists: _Summarize the domain boundary and why it was split out._
- In scope: _List the work this stream owns._
- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._
- Required skills: _List the exact repo-local skills to read before starting._
- Required references: _List the exact repo-local references to read before starting._
- Why this stream exists: `cuda` already covers the old V100 capability surface, but several live skills and references still handed work to `cuda-v100`.
- In scope: update active skill handoffs, fix live reference wording, convert `cuda-v100` into a deprecated shim, and refresh UI metadata.
- Out of scope / dependencies: do not rewrite historical todo ledgers or remove the legacy reference files under `cuda-v100/references/`.
- Required skills: `todo-orchestrator`, `skill-creator`, `cuda`, `v100-model-design`, `native-debugging`, `compare-benchmarks`.
- Required references: `cuda/SKILL.md`, `cuda-v100/SKILL.md`, `native-debugging/references/cuda-follow-on.md`, `compare-benchmarks/references/cuda-follow-on.md`, and `v100-model-design/SKILL.md`.

## Planning Notes
- Treat this as a routing migration, not a capability buildout.
- Leave historical `cuda-v100` wording only where it documents the deprecation boundary or preserves the compatibility shim.

## Assumptions
- The maintained implementation path for V100 work now lives under `cuda` and its native Volta router.
- Legacy `cuda-v100/references/` files can remain on disk as compatibility baggage as long as no active skill routes into them by default.

## Suggested Skills
- `todo-orchestrator` - Track the deprecation as a resumable multi-file migration.
- `skill-creator` - Keep the shim and metadata concise rather than cloning the old router again.
- `cuda` - Primary active CUDA route that now absorbs all live handoffs.

## Useful Reference Files
- `cuda/SKILL.md` - Primary route that should replace all active `cuda-v100` handoffs.
- `native-debugging/references/cuda-follow-on.md` - Follow-on route that previously pointed into `cuda-v100`.
- `compare-benchmarks/references/cuda-follow-on.md` - Comparison follow-on route that previously pointed into `cuda-v100`.
- `v100-model-design/SKILL.md` - Design skill that previously handed implementation work to `cuda-v100`.

## Plan
_None recorded yet._

## Tasks
- [x] Replace live `cuda-v100` cross-skill handoffs with `cuda`.
- [x] Convert `cuda-v100` into a deprecated compatibility shim with refreshed UI metadata.
- [x] Validate that no non-legacy live routing surface still hands work to `cuda-v100`.

## Blockers
_None recorded yet._

## Progress Notes
- Migrated active handoffs in `v100-model-design`, `native-debugging`, `compare-benchmarks`, and the active `cuda` references from `cuda-v100` to `cuda`.
- Replaced the old `cuda-v100/SKILL.md` router with a short deprecated compatibility shim and updated `cuda-v100/agents/openai.yaml` to match.
- Validated that no live non-legacy routing surfaces outside `cuda-v100/` or historical todo ledgers still hand work to `cuda-v100`.

## Next Actions
- No immediate action; leave the legacy `cuda-v100/references/` files on disk unless the user later asks for full removal rather than deprecation.

## Done Criteria
- Active skills and live references route V100 and CUDA follow-on work to `cuda` rather than `cuda-v100`.
- `cuda-v100` remains only as a clearly marked compatibility shim.
- The remaining non-historical `cuda-v100` mentions are compatibility or historical notes rather than live routing instructions.
