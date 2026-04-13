# Current Objective

## Summary
Add summary-first crash-debugging support to `cuda-v100` so standalone CUDA/C++ binaries can be triaged with compact wrapper scripts before escalating to raw debugger output.

## Planning Notes
- The current skill has profiler wrappers and benchmark summaries but no dedicated crash or debugger route.
- This machine has `cuda-gdb`, `compute-sanitizer`, and `cuda-memcheck`, but not plain `gdb` or `coredumpctl`.
- The new path should cover broader CUDA hard failures, not just literal host segfaults.

## Assumptions
- Default workflow is lightweight crash capture, then `compute-sanitizer`, then batch `cuda-gdb` only if needed.
- First-version scope is standalone CUDA/C++ binaries. Torch extension crashes should be documented as a follow-on route, not the main surface.
- The scripts should emit `summary.txt` and `summary.json` first so tool-driven reading stays low-context.

## Suggested Skills
- `cuda-v100` - Primary skill being extended.
- `skill-creator` - Keep the skill update concise, routed, and script-heavy.
- `todo-orchestrator` - Track the workstream and validation in the repo ledger.

## Useful Reference Files
- `cuda-v100/SKILL.md` - Add the crash-debugging route and common sequences.
- `cuda-v100/references/v100_profiling_interpretation.md` - Keep profiling distinct from crash triage.
- `cuda-v100/references/v100_cuda_cpp_optimize.md` - Add debug-build guidance and crash-route pointers.
- `cuda-v100/references/addendum-torch-extensions.md` - Link extension crashes to the new route without making it primary.
- `cuda-v100/scripts/profile_nsys.sh` - Existing summary-first shell-wrapper pattern.
- `cuda-v100/scripts/analyze_nsys_stats.py` - Existing compact JSON and text summary pattern.

## Plan
- Add a dedicated crash-debugging route and reference set to `cuda-v100`.
- Implement crash, sanitizer, and batch `cuda-gdb` wrappers plus compact Python classifiers and summary combiners.
- Update nearby docs and metadata so crashes route into the new workflow before profiling.
- Validate the wrappers with synthetic segfault and CUDA illegal-access style smoke tests.

## Tasks
- [x] Patch todo ledger for crash-debugging workstream
- [x] Add crash-debugging route and references to `cuda-v100`
- [x] Implement crash-debugging helper scripts
- [x] Validate scripts and close ledger state

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the crash-debugging workstream and captured the intended summary-first debugging scope.
- Added `addendum-crash-debugging`, `crash-triage-playbook`, `compute-sanitizer-playbook`, `cuda-gdb-playbook`, and `crash-signature-map`.
- Added `debug_crash.sh`, `debug_compute_sanitizer.sh`, `debug_cuda_gdb.sh`, `classify_cuda_failure.py`, and `combine_debug_summaries.py`.
- Updated `SKILL.md`, `agents/openai.yaml`, `v100_profiling_interpretation.md`, `v100_cuda_cpp_optimize.md`, and `addendum-torch-extensions.md` to expose the new route and keep it distinct from profiling.
- Validated the route with `quick_validate.py`, syntax checks, a synthetic host segfault capture, a CUDA illegal-access `compute-sanitizer` run, and a batch `cuda-gdb` backtrace extraction run.

## Next Actions
- No immediate action; resume only if the user wants Torch-extension-specific crash wrappers or deeper debugger command scripting.

## Done Criteria
- `cuda-v100` can route crash and debugger questions into a dedicated crash-debugging addendum.
- The new scripts emit compact `summary.txt` and `summary.json` artifacts for crash capture, sanitizer runs, and batch `cuda-gdb`.
- The docs keep crash triage separate from profiler workflows.
- The helper scripts are smoke-tested on representative synthetic crash cases.
