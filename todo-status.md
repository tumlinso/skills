# Todo Status

## Summary
Use this file as the quick pickup register for `todos.md` workstreams.
- `ready`: planned work that can be started now.
- `claimed`: currently being written; choose another stream.
- `idle`: unfinished but resumable; safe to pick up.
- `closed`: completed or removed from pickup rotation.

## Workstreams
- `cuda-v100-ptx-splitter` | status: done | execution: closed | owner: codex | file: `todos/cuda-v100-ptx-splitter.md` | next: Implementation complete; wait for explicit todo-cleanup or the next repo task.
- `cuda-v100-ptx-hot-paths` | status: done | execution: closed | owner: codex | file: `todos/cuda-v100-ptx-hot-paths.md` | next: Implementation complete; wait for explicit todo-cleanup or the next repo task.
- `cuda-v100-cpu-porting` | status: done | execution: closed | owner: unassigned | file: `todos/cuda-v100-cpu-porting.md` | next: cuda v100 cpu porting
- `openacc-porting` | status: done | execution: closed | owner: unassigned | file: `todos/openacc-porting.md` | next: create a standalone openacc-porting skill
- `compare-benchmarks-skill` | status: done | execution: closed | owner: unassigned | file: `todos/compare-benchmarks-skill.md` | next: compare benchmarks skill
- `v100-model-design-low-level-ml` | status: done | execution: closed | owner: unassigned | file: `todos/v100-model-design-low-level-ml.md` | next: add low-level ML boundary design guidance to v100-model-design
- `cuda-v100-crash-debugging` | status: done | execution: closed | owner: unassigned | file: `todos/cuda-v100-crash-debugging.md` | next: add summary-first crash and debugger helpers to cuda-v100
- `todo-orchestrator-status-cleanup` | status: done | execution: closed | owner: codex | file: `todos/todo-orchestrator-status-cleanup.md` | next: Run skill-level validation and sync the repo ledgers to the new format.
- `native-debugging` | status: done | execution: closed | owner: codex | file: `todos/native-debugging.md` | next: Implementation complete; wait for explicit todo-cleanup or the next repo task.
- `build-a-new-primary-cuda-skill-by-copying-cuda-v100-expanding-volta-native-depth-and-adding-deep-architecture-specific-optimization-diagnostics-and-profiling-guidance-for-ampere-hopper-blackwell-and-gb200-nvl72` | status: done | execution: closed | owner: codex | file: `todos/build-a-new-primary-cuda-skill-by-copying-cuda-v100-expanding-volta-native-depth-and-adding-deep-architecture-specific-optimization-diagnostics-and-profiling-guidance-for-ampere-hopper-blackwell-and-gb200-nvl72.md` | next: Implementation complete; wait for explicit todo-cleanup or the next CUDA-skill expansion request.
- `deepen-the-primary-cuda-skill-with-more-intense-native-v100-optimization-addendums-and-low-level-scripts-then-expand-ampere-hopper-and-blackwell-path-coverage-toward-cuda-v100-style-routing-parity` | status: done | execution: closed | owner: codex | file: `todos/deepen-the-primary-cuda-skill-with-more-intense-native-v100-optimization-addendums-and-low-level-scripts-then-expand-ampere-hopper-and-blackwell-path-coverage-toward-cuda-v100-style-routing-parity.md` | next: Implementation complete; wait for explicit todo-cleanup or the next CUDA-skill expansion request.
- `make-the-cuda-volta-router-fully-cover-the-old-cuda-v100-domain-so-the-native-path-genuinely-supersedes-the-legacy-skill` | status: done | execution: closed | owner: codex | file: `todos/make-the-cuda-volta-router-fully-cover-the-old-cuda-v100-domain-so-the-native-path-genuinely-supersedes-the-legacy-skill.md` | next: Implementation complete; wait for explicit todo-cleanup or the next CUDA-skill expansion request.
- `deprecate-cuda-v100-by-routing-live-handoffs-to-cuda-and-leaving-only-a-compatibility-shim` | status: done | execution: closed | owner: codex | file: `todos/deprecate-cuda-v100-by-routing-live-handoffs-to-cuda-and-leaving-only-a-compatibility-shim.md` | next: Implementation complete; leave `cuda-v100` as a shim unless full removal is explicitly requested.
- `cuda-context-routing-refactor` | status: done | execution: closed | owner: codex | file: `todos/cuda-context-routing-refactor.md` | next: Implementation complete; wait for explicit cleanup or further routing refinements.
- `cpp-context-compiler` | status: done | execution: closed | owner: codex | file: `todos/cpp-context-compiler.md` | next: Implementation complete; extend only when a real C++ repository exposes a missing semantic edge or transformation proof.

## Staleness Review
_No staleness review recorded yet._

## Cleanup Status
- Cleanup mode is explicit only.
- Safe to call `todo-cleanup`: yes, every tracked workstream is done or superseded.
