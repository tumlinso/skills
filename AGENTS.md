# Repo Guidance

<!-- todo-orchestrator:start -->
## Workflow Ledger

- For substantial multi-step work, consult `todos.md` first.
- Consult `todo-status.md` for pickup-ready, claimed, and idle workstreams before starting parallel work.
- Treat `todos.md` as the canonical active plan and progress ledger.
- For concurrent workstreams, consult the relevant file under `todos/`.
- In plan mode, consult `todo-orchestrator/references/planning-workflow.md`.
- In implementation mode, continue from the recorded plan non-interactively unless truly blocked.
- Prefer relevant repo-local skills and reference files when they match the task.
<!-- todo-orchestrator:end -->

## Skill Routing

- Route OpenACC assessment and incremental OpenACC porting work to `openacc-porting`.
- Default OpenACC work to a review-first workflow with an `openacc-review.md` artifact.
- Compare CPU and OpenACC paths only after correctness is stable; use `compare-benchmarks` if the real task becomes building a fair A/B benchmark harness.
