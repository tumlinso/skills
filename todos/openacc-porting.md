# Current Objective

## Summary
Create a standalone `openacc-porting` skill that starts in review mode, emits a structured `openacc-review.md` artifact, and supports incremental OpenACC implementation without expanding into generic benchmarking or CUDA work.

## Planning Notes
- The repo pattern is a compact `SKILL.md`, `agents/openai.yaml`, optional `references/`, optional `scripts/`, and `unittest` coverage.
- `compare-benchmarks` already provides the right benchmark-contract and summary-first language, so the new skill should borrow that doctrine instead of cloning its harness scripts.

## Assumptions
- `openacc-porting` belongs as a new top-level sibling skill under `/home/tumlinson/.agents/skills`.
- The skill should stay review-first even when it supports implementation.
- Benchmark follow-on should stay documentation-level here and route into `compare-benchmarks` if true A/B harness work is needed.

## Suggested Skills
- `openacc-porting` - Primary skill being created.
- `compare-benchmarks` - Source of benchmark-contract and summary-first validation patterns.
- `todo-orchestrator` - Ledger and execution tracking.

## Useful Reference Files
- `compare-benchmarks/references/comparison-contract.md` - Shared-scenario benchmark contract.
- `compare-benchmarks/references/profiler-workflow.md` - Summary-first profiler interpretation.
- `cuda-v100/references/addendum-nvhpc-cpp.md` - Nearby offload language and constraint framing.

## Plan
- Replace the scaffolded skill template with a single-skill two-mode OpenACC workflow.
- Add the review, data-region, directive, blockers, validation, benchmark-follow-on, and examples references.
- Add small helper scripts for candidate summarization and review generation.
- Add `unittest` coverage for candidate classification and review artifact generation.
- Update root routing and ledger files, then validate the finished skill.

## Tasks
- [x] Initialize the skill scaffold
- [x] Write `SKILL.md` and `agents/openai.yaml`
- [x] Add reference files
- [x] Add helper scripts
- [x] Add tests
- [x] Update `AGENTS.md` and `todos.md`
- [x] Validate the new skill

## Blockers
_None recorded yet._

## Progress Notes
- Used `skill-creator` to initialize the new skill in the repo-consistent location.
- Replaced the scaffold with a review-first router that keeps review and implementation inside one skill.
- Added concise references for review, data regions, directives, blockers, validation, benchmark follow-on, and examples.
- Added `summarize_openacc_candidates.py` and `generate_openacc_review.py` with shared classification logic.
- Added unit tests covering classification and review artifact generation.
- Validated the skill with `python -m unittest discover -s openacc-porting/tests` and `quick_validate.py`.

## Next Actions
- No immediate action; resume only if the user wants deeper examples, compiler-specific OpenACC notes, or broader benchmark tooling.

## Done Criteria
- `openacc-porting` exists as one skill with explicit review and implementation modes.
- The skill writes or refreshes `openacc-review.md` and teaches data-region planning and staged implementation.
- Benchmark follow-on guidance reuses `compare-benchmarks` doctrine without duplicating its harness scripts.
- The skill passes repo-style tests and `quick_validate.py`.
