---
slug: "cuda-v100-ptx-splitter"
status: "done"
execution: "closed"
owner: "codex"
created_at: "2026-04-13T15:33:00Z"
last_heartbeat_at: "2026-04-13T15:49:09Z"
last_reviewed_at: "2026-04-13T15:49:09Z"
stale_after_days: 14
objective: "Add an AST-driven helper to split multi-kernel CUDA translation units into focused single-kernel sources"
---

# Current Objective

## Summary
Add a real helper to `cuda-v100` that uses local libclang to list kernels in a `.cu` file and extract one named kernel plus recursively referenced same-file declarations into a focused source suitable for PTX and SASS inspection.

## Quick Start
- Why this stream exists: the PTX route currently tells users to isolate hot paths, but there is no concrete helper for splitting a multi-kernel compilation unit into one focused source.
- In scope: one new splitter script, supporting docs, one multi-kernel example asset, and validation against the existing PTX dump wrapper.
- Out of scope / dependencies: full refactoring of arbitrary CUDA libraries, build-system integration, or non-CUDA source splitting.
- Required skills: `cuda-v100`, `skill-creator`, `todo-orchestrator`.
- Required references: `cuda-v100/SKILL.md`, `cuda-v100/references/addendum-ptx-routing.md`, `cuda-v100/references/ptx-volta-extreme.md`, `cuda-v100/references/v100_cuda_cpp_optimize.md`, `cuda-v100/scripts/dump_ptx_hotspot.sh`.

## Planning Notes
- The environment has `libclang.so` but not the Python `clang` bindings, so the helper should use direct `ctypes` calls to libclang.
- The first version should be explicit about its scope: free functions and same-file declarations in global or namespace scope, with manifest output for unresolved references.
- The helper should emit a focused source file plus `summary.txt` and `manifest.json`.

## Assumptions
- The default architecture context remains `sm_70`.
- The splitter should preserve file preamble and include directives, then emit only the selected declarations and their same-file dependencies.
- If the source cannot be reconstructed cleanly, the helper should report a partial result instead of pretending the extracted file is complete.

## Suggested Skills
- `cuda-v100` - Primary skill being extended.
- `skill-creator` - Keep the helper and docs concise and capability-focused.
- `todo-orchestrator` - Track the new workstream and validation.

## Useful Reference Files
- `cuda-v100/SKILL.md`
- `cuda-v100/references/addendum-ptx-routing.md`
- `cuda-v100/references/ptx-volta-extreme.md`
- `cuda-v100/references/v100_cuda_cpp_optimize.md`
- `cuda-v100/scripts/dump_ptx_hotspot.sh`
- `cuda-v100/scripts/summarize_ptx_dump.py`

## Plan
- Add a libclang-driven splitter script that can list kernels and extract one focused source from a multi-kernel `.cu`.
- Add a multi-kernel example and route documentation that explains when to use the splitter before PTX dumping.
- Validate the splitter on the example source and run the extracted source through the existing PTX dump wrapper.

## Tasks
- [x] Create PTX splitter workstream ledger
- [x] Implement the AST-driven splitter script
- [x] Add example assets and doc updates
- [x] Validate splitter output and close the workstream

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the PTX splitter workstream and confirmed the local environment exposes `libclang.so` but not Python `clang` bindings.
- Added `split_cuda_translation_unit.py`, using direct `ctypes` calls into `libclang.so` to list kernels and extract one named kernel plus same-file helper declarations into a focused source.
- Added `multi_kernel_unit_example.cu` and updated the PTX docs and script guidance so multi-kernel `.cu` files route through the splitter before PTX dumping.
- Validated the splitter with kernel listing, focused extraction for `kernel_beta`, a successful `dump_ptx_hotspot.sh` run on the extracted source, and `quick_validate.py`.

## Next Actions
- No immediate action; resume only if the splitter needs deeper dependency recovery or build-system-aware extraction.

## Done Criteria
- `cuda-v100` ships a helper that can list kernels and extract one named kernel plus same-file helpers from a multi-kernel `.cu`.
- The helper emits a focused source file, `summary.txt`, and `manifest.json`.
- The docs say when to use the splitter before running the PTX dump wrapper.
- The extracted example source compiles through the existing `sm_70` PTX dump workflow.
