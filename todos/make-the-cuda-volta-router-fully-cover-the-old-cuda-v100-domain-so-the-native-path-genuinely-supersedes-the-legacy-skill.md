---
slug: "make-the-cuda-volta-router-fully-cover-the-old-cuda-v100-domain-so-the-native-path-genuinely-supersedes-the-legacy-skill"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-14T12:22:04Z"
last_heartbeat_at: "2026-04-14T12:25:10Z"
last_reviewed_at: "2026-04-14T12:25:10Z"
stale_after_days: 14
objective: "Make the cuda Volta router fully cover the old cuda-v100 domain so the native path genuinely supersedes the legacy skill."
---

# Current Objective

## Summary
Make the cuda Volta router fully cover the old cuda-v100 domain so the native path genuinely supersedes the legacy skill.

## Quick Start
- Why this stream exists: _Summarize the domain boundary and why it was split out._
- In scope: _List the work this stream owns._
- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._
- Required skills: _List the exact repo-local skills to read before starting._
- Required references: _List the exact repo-local references to read before starting._
- Why this stream exists: the new `cuda` skill cannot truly supersede `cuda-v100` for native work until the Volta router can reach the entire old V100 domain.
- In scope: add the missing Volta route rows, restore the old navigation scaffolding, re-add the `v100-model-design` handoff, and expose the full Volta script surface from the new router.
- Out of scope: non-Volta family deepening beyond whatever is needed to keep the top-level `cuda` skill coherent.
- Required skills: `todo-orchestrator`, `cuda`, and the legacy `cuda-v100` route shape.
- Required references: `cuda/references/architectures/volta/router.md`, `cuda-v100/SKILL.md`, and the copied Volta references and scripts already present under `cuda/`.

## Planning Notes
- The missing work is router reachability, not missing underlying Volta content or scripts.
- The safest way to close the gap is to mirror the old `cuda-v100` navigation scaffolding while keeping the stronger new Volta-specific addendums in front of it.
- The updated router should make it obvious that the native path now fully covers memory, topology, pipeline, crash, kernel mechanics, hot kernel, Tensor Cores, CPU-porting, PTX, NVHPC, Torch extensions, sparse bio, and benchmark standardization.

## Assumptions
- The old `cuda-v100` navigation model is still the best completeness baseline for native Volta routing.
- The stronger new Volta-native addendums should be integrated into that model rather than replacing it with a shorter router.

## Suggested Skills
- `todo-orchestrator` - Track the native-router completion as a dedicated resumable workstream.
- `cuda` - Primary skill being corrected so it can truly supersede the legacy V100 path.
- `cuda-v100` - Reference route-shape and domain coverage baseline.

## Useful Reference Files
- `cuda/references/architectures/volta/router.md` - Target file that must become the full native super-router.
- `cuda-v100/SKILL.md` - Legacy Volta route map to mirror and adapt.
- `cuda/references/architectures/volta/native-v100-extreme.md` - Stronger new native addendum that should stay in the upgraded router.
- `cuda/SKILL.md` - Top-level router that should still point cleanly into the completed Volta route.

## Plan
_None recorded yet._

## Tasks
- [x] Expand the Volta router to expose all old `cuda-v100` route classes.
- [x] Restore Volta-specific opening moves, base-manual guidance, support-map chaining, common sequences, and scripts-by-situation navigation.
- [x] Re-add the `v100-model-design` handoff for native Volta model-family or architecture-build questions.
- [x] Validate the updated `cuda` skill and sync the ledger.

## Blockers
_None recorded yet._

## Progress Notes
- Opened a focused workstream to close the remaining native-router completeness gap between `cuda` and `cuda-v100`.
- Rewrote `cuda/references/architectures/volta/router.md` as the native super-router over the old `cuda-v100` domain rather than a shorter summary router.
- Added the missing native route rows for Tensor Core routing, CPU-porting, NVHPC, Torch extensions, sparse bio, and benchmark standardization.
- Restored the old Volta navigation scaffolding: path-specific opening moves, base-manual guidance, support-map chaining, common sequences, and the full scripts-by-situation surface.
- Re-added the `v100-model-design` handoff in both the top-level `cuda` skill and the Volta router, and re-validated the updated `cuda` skill with quick_validate.py.

## Next Actions
- Rewrite `cuda/references/architectures/volta/router.md` as a full super-router over the old `cuda-v100` domain.
- No immediate action; the native Volta path now reaches the full old `cuda-v100` domain from the new `cuda` skill.

## Done Criteria
- The Volta router in `cuda` can directly reach the full old `cuda-v100` domain from the new skill.
- The router includes the legacy navigation scaffolding plus the stronger new Volta-native addendums and script surface.
- The updated `cuda` skill validates cleanly.
