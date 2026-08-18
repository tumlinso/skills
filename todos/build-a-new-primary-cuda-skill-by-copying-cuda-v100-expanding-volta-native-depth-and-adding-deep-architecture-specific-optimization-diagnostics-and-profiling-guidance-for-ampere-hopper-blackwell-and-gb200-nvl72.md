---
slug: "build-a-new-primary-cuda-skill-by-copying-cuda-v100-expanding-volta-native-depth-and-adding-deep-architecture-specific-optimization-diagnostics-and-profiling-guidance-for-ampere-hopper-blackwell-and-gb200-nvl72"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-14T10:30:58Z"
last_heartbeat_at: "2026-04-14T10:40:19Z"
last_reviewed_at: "2026-04-14T10:40:19Z"
stale_after_days: 14
objective: "Build a new primary cuda skill by copying cuda-v100, expanding Volta/native depth, and adding deep architecture-specific optimization, diagnostics, and profiling guidance for Ampere, Hopper, Blackwell, and GB200 NVL72."
---

# Current Objective

## Summary
Build a new primary cuda skill by copying cuda-v100, expanding Volta/native depth, and adding deep architecture-specific optimization, diagnostics, and profiling guidance for Ampere, Hopper, Blackwell, and GB200 NVL72.

## Quick Start
- Why this stream exists: _Summarize the domain boundary and why it was split out._
- In scope: _List the work this stream owns._
- Out of scope / dependencies: _List handoffs, upstream dependencies, or adjacent streams._
- Required skills: _List the exact repo-local skills to read before starting._
- Required references: _List the exact repo-local references to read before starting._
- Why this stream exists: replace the practical role of `cuda-v100` with a broader primary `cuda` skill while improving the native Volta path.
- In scope: copy `cuda-v100`, deepen native/V100 guidance, add Ampere/Hopper/Blackwell plus GB200 NVL72 routing, and expand diagnostics/profiling/low-level scripts.
- Out of scope: consumer GPU-specific doctrine, H200-specific routing, and automatic cleanup of old workstreams.
- Required skills: `todo-orchestrator`, `skill-creator`, and `cuda-v100` patterns from the existing skill.
- Required references: `cuda-v100/SKILL.md`, `cuda-v100/references/v100_programming_guide.md`, `cuda-v100/references/v100_cuda_cpp_optimize.md`, and NVIDIA architecture tuning guides used during implementation.

## Planning Notes
- The new `cuda` skill should keep context minimal by routing through system profile, architecture family, then bottleneck-specific subrouters.
- Volta/native remains the strongest route and should exceed the current `cuda-v100` depth rather than merely preserving it.
- Diagnostics helpers should summarize benchmark, profiler, debugger, and dump output so the skill can consume concise artifacts instead of raw logs.

## Assumptions
- `cuda-v100` remains unchanged on disk for compatibility while `cuda` becomes the maintained primary skill.
- The canonical native machine remains the current 4xV100 diagonal-NVLink host.
- Blackwell deployment guidance is anchored on GB200 NVL72 rather than generic rack assumptions.

## Suggested Skills
- `todo-orchestrator` - Track the substantial multi-step skill buildout in the shared ledger.
- `skill-creator` - Keep the new skill segmented, concise, and validated as a real standalone skill.
- `cuda-v100` - Reuse and improve existing Volta routing, profiling, and low-level optimization patterns.

## Useful Reference Files
- `cuda-v100/SKILL.md` - Source skill to copy and reorganize into the new primary `cuda` skill.
- `cuda-v100/references/v100_programming_guide.md` - Current Volta system and optimization doctrine to preserve and deepen.
- `cuda-v100/references/v100_cuda_cpp_optimize.md` - Current low-level CUDA/C++ rules and profiler guidance to refactor into family-local docs.
- `todo-orchestrator/references/todo-format.md` - Canonical workstream format for keeping this task resumable.

## Plan
- Clone `cuda-v100` into `cuda` and inspect the copied surface for high-value refactor boundaries.
- Research Ampere, Hopper, Blackwell, and GB200 NVL72 sources and distill architecture-specific optimization doctrine.
- Refactor the new skill into top-level system and family routers plus diagnostics-heavy scripts.
- Deepen the Volta/native path beyond current `cuda-v100` content, then validate the new skill.

## Tasks
- [x] Clone `cuda-v100` into a new `cuda` skill scaffold.
- [x] Research and distill architecture-specific doctrine for Ampere, Hopper, Blackwell, and GB200 NVL72.
- [x] Refactor `cuda/SKILL.md`, metadata, and reference layout into system/family routers.
- [x] Expand diagnostics, profiling, dump-filtering, and architecture-specific build helpers.
- [x] Validate the new `cuda` skill and sync ledger state.

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the new `cuda` workstream and recorded the expected routing, research, and diagnostics scope.
- Copied `cuda-v100` into a new `cuda` skill, rewrote the top-level router, and added system-first plus architecture-family routing.
- Added new focused references for native V100, Ampere, Hopper, Blackwell, GB200 NVL72, and cross-cutting code-organization and diagnostics doctrine.
- Added segmented build and diagnostics helpers for narrow architecture-specific builds, single-kernel TU checks, focused objdump filtering, and compact summary merging.
- Validated the new skill with quick_validate.py, compiled the new Python scripts, and smoke-tested the new build, dump-filtering, TU-check, and summary helpers.

## Next Actions
- Copy `cuda-v100` to `cuda`, then start the architecture/system split from the copied baseline.
- No immediate action; extend the family packs or diagnostics helpers only if a concrete CUDA workload exposes a missing route.

## Done Criteria
- `cuda` exists as a standalone primary skill with system-first and family-first routing that preserves and improves the Volta/native path.
- The new skill contains deep architecture-specific optimization doctrine for Ampere, Hopper, Blackwell, and GB200 NVL72 without an H200-specific branch.
- The diagnostics surface includes strong summary-first helpers for profiling, debugging, and low-level dump filtering.
- The new `cuda` skill exists as a primary CUDA route with stronger native Volta guidance than the copied baseline.
- The skill contains dedicated system and architecture references for native, GB200 NVL72, Volta, Ampere, Hopper, and Blackwell.
- The skill exposes summary-first profiling, debugging, and low-level dump-filtering helpers under a segmented script layout.
