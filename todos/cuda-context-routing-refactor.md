---
slug: "cuda-context-routing-refactor"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-19T12:10:32Z"
last_heartbeat_at: "2026-04-19T12:22:06Z"
last_reviewed_at: "2026-04-19T12:10:32Z"
stale_after_days: 14
objective: "refactor the cuda skill into a dense two-stage routing tree with narrower context usage and stronger script-backed route selection"
---

# Current Objective

## Summary
Refactor the cuda skill into a denser two-stage routing tree that reaches the same optimization depth with less context.

## Quick Start
- Why this stream exists: _Summarize the domain boundary and why it was split out._
- In scope: _List the work this stream owns._
- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._
- Required skills: _List the exact repo-local skills to read before starting._
- Required references: _List the exact repo-local references to read before starting._
- Use skill-creator to keep the rewritten skill dense and progressively disclosed.
- Use todo-orchestrator to keep the ledger current while refactoring multiple docs and scripts.
- Start in cuda/SKILL.md, then shrink family routers, then add micro-routers and decision scripts.
- Validate with skill-level checks plus script smoke tests after the routing tree stabilizes.

## Planning Notes
_None recorded yet._

## Assumptions
- Path churn is allowed if the new routing tree is materially cleaner.
- Dense prose is preferred over human-friendly explanatory text.
- High-value decision scripts should recommend the next narrow route instead of only summarizing profiler artifacts.

## Suggested Skills
- `skill-creator` - Keep the skill dense, segmented, and progressively disclosed.
- `todo-orchestrator` - Track this substantial refactor in todos.md and todo-status.md.

## Useful Reference Files
- `cuda/SKILL.md` - Current top-level routing surface to compress.
- `cuda/references/architectures/volta/router.md` - Largest route fan-out and main context hog.
- `cuda/references/v100_cuda_cpp_optimize.md` - Largest Volta implementation manual to split.
- `cuda/references/v100_programming_guide.md` - Second large Volta manual to split.
- `todo-orchestrator/references/todo-format.md` - Ledger format guidance if the workstream file needs manual cleanup.

## Plan
- Compress top-level cuda routing and family routers.
- Split heavy Volta doctrine into narrow micro-routers and deep manuals.
- Add decision scripts for route selection from benchmark, nsys, and ncu artifacts.
- Wire routers to the new micro-routers and script surfaces.
- Run validation and smoke tests, then sync the ledgers.

## Tasks
_None recorded yet._

## Blockers
_None recorded yet._

## Progress Notes
- Opened the cuda-context-routing-refactor workstream and scoped it around routing compression plus script-backed delegation.
- Rewrote cuda/SKILL.md into a denser public router with script-first diagnostics and explicit micro-router discipline.
- Replaced the oversized Volta router with a compact route table and added narrow Volta micro-routers for native, fusion, hot-kernel, tensor, torch-op, and benchmark flows.
- Added scripts/common/recommend_cuda_route.py and extended nsys, ncu, and combined benchmark summaries with machine-readable recommended_route fields.
- Updated Ampere, Hopper, and Blackwell routers to use the shared route recommender when profiler or benchmark summaries already exist.
- Validated the cuda skill with quick_validate.py, compiled the edited Python scripts, and smoke-tested the route recommender plus combined summary routing output.

## Next Actions
- Inspect the current top-level and family routing files, then patch the new dense two-stage tree.
- No immediate action; extend the route recommender only if real workloads expose missing route labels or ambiguous follow-on decisions.

## Done Criteria
- The cuda skill reaches the same major optimization surfaces with less default context.
- Family routers and Volta routing no longer default into broad manuals for routine follow-on questions.
- Profiler decision scripts can emit a concrete next route instead of generic summary-only advice.
- The rewritten skill validates and the new scripts pass syntax or smoke tests.
