---
slug: "cuda-v100-ptx-hot-paths"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-13T14:52:16Z"
last_heartbeat_at: "2026-04-13T15:10:41Z"
last_reviewed_at: "2026-04-13T15:10:41Z"
stale_after_days: 14
objective: "Add a Volta-first PTX hot-path workflow with focused dump scripts and examples"
---

# Current Objective

## Summary
Strengthen `cuda-v100` so explicit PTX requests on Tesla V100 route into a concrete `sm_70` workflow centered on isolated hot paths, focused PTX/SASS dumps, and small example artifacts instead of monolithic code dumps.

## Quick Start
- Why this stream exists: the current PTX path explains principles but does not yet provide a concrete Volta-specific inspection workflow, helper scripts, or examples.
- In scope: `cuda-v100` PTX routing/docs, helper scripts, compact example artifacts, `agents/openai.yaml`, and ledger updates.
- Out of scope / dependencies: general benchmark harness changes, non-PTX CUDA routes, and unrelated skill refactors.
- Required skills: `cuda-v100`, `skill-creator`, `todo-orchestrator`.
- Required references: `cuda-v100/SKILL.md`, `cuda-v100/references/addendum-ptx-routing.md`, `cuda-v100/references/ptx-general-guidelines.md`, `cuda-v100/references/ptx-volta-extreme.md`, `cuda-v100/references/v100_cuda_cpp_optimize.md`, `todo-orchestrator/references/todo-format.md`.

## Planning Notes
- The PTX route should stay request-only.
- For explicit V100 PTX requests, the default follow-on should bias toward the Volta-specific path rather than staying portable-first.
- Dump scripts should prefer isolated hot kernels or micro-primitives so generated PTX/SASS stays small enough for inspection and model context.

## Assumptions
- The helper scripts should emit `summary.txt` and `summary.json` first, matching the repo's summary-first pattern.
- Example artifacts should be runnable and small, not a benchmark suite.
- Separate headers or narrow translation units are the default structure for optimization targets because they bound disassembly output cleanly.

## Suggested Skills
- `cuda-v100` - Primary skill being extended.
- `skill-creator` - Keep the skill compact while adding scripts, references, and examples.
- `todo-orchestrator` - Keep the workstream ledger synchronized during implementation.

## Useful Reference Files
- `cuda-v100/SKILL.md`
- `cuda-v100/references/addendum-ptx-routing.md`
- `cuda-v100/references/ptx-general-guidelines.md`
- `cuda-v100/references/ptx-volta-extreme.md`
- `cuda-v100/references/ptx-sparse-bio-hotpaths.md`
- `cuda-v100/references/v100_cuda_cpp_optimize.md`
- `cuda-v100/scripts/profile_ncu.sh`
- `cuda-v100/scripts/analyze_ncu_csv.py`

## Plan
- Update `cuda-v100` PTX routing to make hot-path isolation explicit and bias explicit V100 PTX requests toward the Volta-specific reference.
- Rewrite the Volta PTX reference into a concrete `sm_70` workflow centered on SASS inspection, resource tradeoffs, and bounded hot-path dumps.
- Add focused PTX/SASS dump helper scripts and compact mixed example artifacts.
- Validate scripts, examples, and skill metadata, then close the workstream.

## Tasks
- [x] Create PTX hot-path workstream ledger
- [x] Patch PTX routing and reference docs
- [x] Add PTX helper scripts and mixed examples
- [x] Validate changes and close the workstream

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the PTX hot-path workstream and recorded the Volta-first, hot-path-isolation scope.
- Updated the PTX routing so explicit V100 PTX requests bias toward the Volta-specific path and require hot-path isolation before deep dumps.
- Added `dump_ptx_hotspot.sh`, `summarize_ptx_dump.py`, and mixed inline-PTX plus standalone-PTX example artifacts under `assets/ptx-examples/`.
- Validated the new workflow with `quick_validate.py`, shell and Python syntax checks, and live wrapper runs on both example surfaces for `sm_70`.

## Next Actions
- No immediate action; resume only if the PTX workflow needs more example kernel families or deeper summary heuristics.

## Done Criteria
- `cuda-v100` routes explicit PTX requests into a Volta-first hot-path isolation workflow on `sm_70`.
- The skill ships focused PTX/SASS dump helpers with `summary.txt` and `summary.json`.
- The PTX references and nearby CUDA docs consistently recommend isolating hot paths into separate headers or narrow translation units before deep inspection.
- The new scripts and example artifacts pass representative smoke tests.
