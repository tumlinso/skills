---
slug: "deepen-the-primary-cuda-skill-with-more-intense-native-v100-optimization-addendums-and-low-level-scripts-then-expand-ampere-hopper-and-blackwell-path-coverage-toward-cuda-v100-style-routing-parity"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-14T10:45:33Z"
last_heartbeat_at: "2026-04-14T10:50:54Z"
last_reviewed_at: "2026-04-14T10:50:54Z"
stale_after_days: 14
objective: "Deepen the primary cuda skill with more intense native V100 optimization addendums and low-level scripts, then expand Ampere, Hopper, and Blackwell path coverage toward cuda-v100-style routing parity."
---

# Current Objective

## Summary
Deepen the primary cuda skill with more intense native V100 optimization addendums and low-level scripts, then expand Ampere, Hopper, and Blackwell path coverage toward cuda-v100-style routing parity.

## Quick Start
- Why this stream exists: _Summarize the domain boundary and why it was split out._
- In scope: _List the work this stream owns._
- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._
- Required skills: _List the exact repo-local skills to read before starting._
- Required references: _List the exact repo-local references to read before starting._
- Why this stream exists: the new `cuda` skill needs a stronger native Volta path and broader family parity before it can truly supersede `cuda-v100`.
- In scope: add more intense V100/native optimization addendums and scripts first, then expand Ampere, Hopper, and Blackwell routes toward full `cuda-v100`-style path coverage.
- Out of scope: consumer GPU doctrine, H200-specific routing, and cleanup of old workstreams.
- Required skills: `todo-orchestrator` for execution discipline and `cuda` plus copied `cuda-v100` patterns for routing shape.
- Required references: `cuda/SKILL.md`, `cuda/references/architectures/volta/router.md`, `cuda-v100/SKILL.md`, and the family-local optimization references already created under `cuda/references/architectures/`.

## Planning Notes
- The first priority is to make the native Volta route more forceful than the copied baseline by adding deeper optimization doctrine and stronger low-level scripts.
- After the Volta pass, the newer architectures should expose a broader path map so the top-level skill can answer more than one generic low-level question per family.
- New scripts should stay summary-first and bounded, with outputs optimized for agent consumption instead of human prose.

## Assumptions
- The stronger V100 route should live in the new `cuda` skill rather than backporting to `cuda-v100`.
- Family parity means broader route coverage and architecture-aware doctrine, not perfect file-for-file duplication of every Volta reference.
- The existing common scripts and copied Volta references remain available while the new family-local surfaces deepen.

## Suggested Skills
- `todo-orchestrator` - Track the follow-on expansion as a separate resumable workstream.
- `cuda` - Primary skill being deepened and brought closer to cross-family parity.
- `cuda-v100` - Reference the older Volta path map when expanding the new family routers.

## Useful Reference Files
- `cuda/SKILL.md` - Current primary router that will gain deeper Volta and broader family routing.
- `cuda/references/architectures/volta/router.md` - Immediate entrypoint for the stronger native Volta path.
- `cuda/references/architectures/volta/native-v100-extreme.md` - Current Volta-specific optimization reference to deepen.
- `cuda-v100/SKILL.md` - Legacy path map to mirror where parity is still missing.

## Plan
- Inspect the copied `cuda` Volta route and identify the missing native-V100 optimization and scripting surfaces.
- Add new Volta-specific addendums and scripts for fusion, register-pressure triage, SASS or ptxas summary, and benchmark loop discipline.
- Expand Ampere, Hopper, and Blackwell routers with broader path maps and family-local guidance where the new `cuda` skill is still shallow.
- Validate the updated skill and close the workstream.

## Tasks
- [x] Add stronger Volta/native optimization references to the `cuda` skill.
- [x] Add stronger Volta/native low-level scripts to the `cuda` skill.
- [x] Expand Ampere, Hopper, and Blackwell route coverage toward `cuda-v100`-style parity.
- [x] Validate the updated `cuda` skill and sync the ledger.

## Blockers
_None recorded yet._

## Progress Notes
- Opened a new follow-on workstream to deepen the new `cuda` skill instead of modifying the closed scaffold workstream retroactively.
- Added new Volta-native references for fusion and specialization, register-pressure triage, native benchmark-loop discipline, and SASS or PTX triage.
- Added new Volta-native helper scripts for profile-build emission, ptxas verbose summarization, focused SASS behavior summarization, and native benchmark-matrix emission.
- Expanded the Ampere, Hopper, and Blackwell family routers with broader path maps and new family-local docs for programming guidance, profiling interpretation, memory-topology, pipeline, kernel mechanics, hot-kernel lab, Tensor Core routing, and PTX routing.
- Validated the updated skill with quick_validate.py, compiled the new Volta Python helpers, and smoke-tested the new ptxas, SASS, build-flag, and benchmark-matrix scripts.

## Next Actions
- Inspect the current Volta route and copied script surface, then add the new native-V100 addendums and helpers first.
- No immediate action; deepen individual family routes further only when a concrete CUDA workload exposes missing doctrine or helper coverage.

## Done Criteria
- The `cuda` skill exposes a stronger native Volta route than the current copied baseline, with additional addendums and low-level helper scripts.
- Ampere, Hopper, and Blackwell each expose broader route coverage so the skill can handle more of the same path classes that `cuda-v100` already covers for Volta.
- The updated skill validates and the new scripts pass syntax or smoke checks.
