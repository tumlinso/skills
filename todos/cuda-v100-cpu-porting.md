# Current Objective

## Summary
Add CPU-centric to CUDA porting guidance to cuda-v100 with a two-track endpoint: offload when regular loops are good enough, native CUDA when control or sparse irregular behavior matters.

## Planning Notes
- The current cuda-v100 skill has decomposition and NVHPC guidance, but no direct CPU-to-CUDA porting route.
- The new material should be algorithmic-rewrite first and biased toward HPC and sparse bioinformatics code.

## Assumptions
- This belongs adjacent to the NVHPC route rather than hidden inside it.
- The preferred endpoint is two-track: directive offload for acceptable regular loops, native CUDA for sparse irregular hot paths.

## Suggested Skills
- `cuda-v100` - Primary skill being extended.
- `todo-orchestrator` - Track the work in todos.md and a workstream ledger.

## Useful Reference Files
- `cuda-v100/references/addendum-nvhpc-cpp.md` - Existing nearby route for offload tradeoffs.
- `cuda-v100/references/v100_programming_guide.md` - General V100 routing and optimization doctrine.
- `cuda-v100/references/v100_bioinformatics_guide.md` - Sparse bioinformatics examples and layout decisions.
- `cuda-v100/references/v100_cuda_cpp_optimize.md` - Low-level CUDA/C++ implementation guidance that should remain downstream of porting decisions.

## Plan
- Add a dedicated CPU-porting route in cuda-v100 and hook it into the existing NVHPC, general V100, and sparse bio flows.
- Create new references for entry routing, offload-vs-native choice, native CUDA rewrite patterns, and sparse bio CPU-porting patterns.
- Update existing references and metadata so the new route is discoverable but does not duplicate low-level docs.

## Tasks
- [x] Patch todo ledger for cpu-porting workstream
- [x] Add CPU-porting route to cuda-v100 SKILL.md
- [x] Create CPU-porting reference set
- [x] Refresh NVHPC, programming, CUDA/C++, and bio guides
- [x] Validate skill and ledger state

## Blockers
_None recorded yet._

## Progress Notes
- Initialized the cuda-v100-cpu-porting workstream and recorded the intended structure.
- Added `addendum-cpu-porting`, `cpu-porting-decision-tree`, `cpu-to-cuda-rewrite-patterns`, and `cpu-porting-sparse-bio`.
- Updated `SKILL.md`, NVHPC routing, general V100 routing, CUDA/C++ optimize guidance, bio guidance, and OpenAI metadata to expose the new CPU-porting path.
- Validated the updated skill with `quick_validate.py`.

## Next Actions
- No immediate action; resume only if the user wants deeper CPU-porting examples or additional scripts.

## Done Criteria
- cuda-v100 can route explicit CPU-centric porting questions into a dedicated set of references.
- The new docs distinguish offload from native CUDA and prioritize algorithmic rewrite first.
- The sparse bio route explains how to port irregular CPU-centric scientific code without copying the CPU decomposition literally.
