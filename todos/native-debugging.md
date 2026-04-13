# Current Objective

## Summary
Create a standalone `native-debugging` skill for Linux-first C/C++ debugging with summary-first helper scripts, concise references, and explicit CUDA debugging follow-on routing into `cuda-v100`.

## Quick Start
- Why this stream exists: the repo has CUDA-specific crash-debugging inside `cuda-v100`, but no general native debugging skill for ordinary C/C++ binaries and mixed native stacks.
- In scope: skill scaffold, router-style `SKILL.md`, UI metadata, focused references, summary-first wrappers, install guidance, validation, and ledger synchronization.
- Out of scope / dependencies: do not remove, rewire, or absorb `cuda-v100`; route CUDA-specific debugging there instead.
- Required skills: `skill-creator`, `todo-orchestrator`
- Required references: `todo-orchestrator/references/todo-format.md`, `cuda-v100/references/addendum-crash-debugging.md`, `cuda-v100/scripts/debug_crash.sh`

## Planning Notes
- Keep the skill Linux-first and Ubuntu-oriented because the host and available tools are Ubuntu 24.04 on x86_64.
- Reuse the summary-first wrapper and classifier shape from `cuda-v100`, but make the new skill general to host-native debugging rather than GPU-specific debugging.
- Include an install checklist because the user explicitly asked for the components they need to install.

## Assumptions
- `gdb` is the primary debugger surface for v1.
- First-class tool routes should be crash capture, sanitizers, `gdb`, symbolization, `strace`, and `perf`.
- `lldb`, `rr`, and `valgrind` may be mentioned as optional tooling, but they are not required v1 wrapper targets.

## Suggested Skills
- `skill-creator` - Primary skill for creating and structuring the new skill.
- `todo-orchestrator` - Ledger and workstream tracking for the multi-step repo change.
- `cuda-v100` - Source of the existing CUDA crash-debugging references and summary-first shell-wrapper pattern.

## Useful Reference Files
- `cuda-v100/references/addendum-crash-debugging.md` - Existing crash-triage structure to mirror without copying CUDA ownership.
- `cuda-v100/scripts/debug_crash.sh` - Existing summary-first wrapper shape to adapt for native debugging.
- `/home/tumlinson/.codex/skills/.system/skill-creator/references/openai_yaml.md` - UI metadata constraints for `agents/openai.yaml`.

## Plan
- Initialize `native-debugging` with `scripts/`, `references/`, and `agents/`.
- Replace the template with a compact router that maps crash, sanitizer, debugger, tracing, symbolization, CPU profiling, and CUDA follow-on requests.
- Add summary-first helper scripts and concise references, including Ubuntu install guidance.
- Validate the skill, smoke-test representative workflows, and close the ledger.

## Tasks
- [x] Initialize the `native-debugging` scaffold
- [x] Write `SKILL.md` and `agents/openai.yaml`
- [x] Add native-debugging reference files
- [x] Add helper scripts
- [x] Validate wrappers and smoke-test representative workflows
- [x] Sync ledger state and close the workstream

## Blockers
_None recorded yet._

## Progress Notes
- Created the workstream ledger and scoped the skill as a standalone Linux-first native debugging surface with CUDA follow-on routing.
- Initialized the skill with `skill-creator`, replaced the template with a router-style `SKILL.md`, and corrected the generated `default_prompt`.
- Added focused references for workflow choice, sanitizer builds, sanitizer interpretation, `gdb`, symbolization, `strace`, `perf`, CUDA follow-on routing, and Ubuntu install components.
- Added summary-first helper scripts for crash capture, batch `gdb`, `strace`, `perf stat`, toolchain inspection, summary classification, and summary combination.
- Validated the skill with `quick_validate.py`, shell syntax checks, Python compilation, a synthetic segfault crash capture, an ASan run, an unsandboxed `gdb` smoke test, an unsandboxed `strace` missing-path smoke test, a `perf stat` smoke test, and a combined-summary smoke test.

## Next Actions
- No immediate action; resume only if the user wants extra wrappers such as `lldb`, `rr`, or `valgrind`, or wants tighter symbolization automation.

## Done Criteria
- `native-debugging` exists as a standalone skill under `/home/tumlinson/.agents/skills`.
- The skill routes Linux-first C/C++ crash, sanitizer, debugger, symbolization, tracing, and lightweight CPU profiling tasks.
- The skill emits compact text and JSON summaries before raw logs.
- CUDA-specific debugging is routed into `cuda-v100` references instead of being duplicated.
- The skill includes an explicit Ubuntu install component checklist.
- The skill passes `quick_validate.py` and representative smoke tests.
