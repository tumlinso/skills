# Current Objective

## Summary
Create a standalone script-heavy skill for comparing implementation A and B under a shared benchmark and profiler contract.

## Planning Notes
- No existing comparison skill exists in the repo; this is a net-new standalone skill rather than an extension of cuda-v100.
- The new skill should own its own harness, mutex, summary, and profiler orchestration scripts, while using cuda-v100 only as an optional downstream CUDA follow-on.

## Assumptions
- The skill will live at .agents/skills/compare-benchmarks and stay general-purpose rather than CUDA-only.
- Benchmark and profiler outputs should be concise and summary-first to minimize context cost.

## Suggested Skills
- `todo-orchestrator` - Track the multi-step skill creation and validation in the ledger.
- `cuda-v100` - Reference existing benchmark-summary and profiler-wrapper patterns without creating a dependency.

## Useful Reference Files
- `cuda-v100/references/benchmark-standardization.md` - Existing summary-first benchmark contract pattern.
- `cuda-v100/references/benchmark-target-authoring.md` - Reference for interoperable benchmark wrapper contracts.
- `cuda-v100/scripts/with_benchmark_mutex.sh` - Existing mutex behavior to mirror in the new skill.

## Plan
- Replace the scaffolded SKILL.md with a comparison-specific routing guide and create agents/openai.yaml.
- Add comparison references for workflow, contract, wrappers, component breakdown, profiling, correctness, and CUDA follow-on routing.
- Add script-heavy harness utilities for mutexing, wrapper initialization, running both implementations, summarizing runs, combining summaries, diffing component breakdowns, and compare-specific profiling.
- Validate the new skill and smoke-test the core scripts on mocked inputs.

## Tasks
- [x] Replace skill skeleton with comparison-specific docs
- [x] Create compare-benchmarks references
- [x] Create compare-benchmarks script suite
- [x] Validate skill and smoke-test scripts

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the compare-benchmarks workstream and captured the intended standalone script-heavy design.
- Replaced the scaffold with a standalone compare-benchmarks skill, UI metadata, and routing docs.
- Added a script-heavy comparison suite: mutex wrapper, harness init, CLI/Python wrapper generators, compare runner, summary combiner, profiler wrappers, and component diff.
- Validated the skill with quick_validate.py, compiled all Python scripts, and smoke-tested the summary pipeline on mocked implementation outputs.

## Next Actions
- No immediate action; extend the profiler wrappers only if a repo needs deeper compare-specific integration.

## Done Criteria
- The new skill can scaffold or normalize implementation A/B wrappers under one benchmark contract.
- The skill owns its own mutex and summary-first profiler workflow.
- The skill stays separate from cuda-v100 while allowing optional CUDA-specific follow-on.
- The skill exists as a standalone compare-benchmarks skill under .agents/skills.
- It can scaffold or normalize implementation A/B wrappers and produce compact comparison summaries.
- It owns its own mutex and summary-first profiler workflow without depending on cuda-v100.
