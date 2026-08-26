# Repo Guidance

<!-- coding-workflow:start -->
## Coding workflow interface

- For substantial repository work, ALWAYS use the `coding-workflow` MCP server first when it is available.
- Do not pre-claim through `todo-orchestrator` or begin repository mutations before `next_task`.
- Call `next_task`, then use `inspect_task` only when bounded source/evidence context is needed.
- `delegate_task` is opportunistic. `local_unavailable` means continue directly in Codex; never wait for a GPU.
- Use `collect_delegation` only for a returned delegation handle and finish every claimed task with `finish_task`.
- After a workflow claim exists, use specialized skills only as bounded execution helpers.
- Existing todo, ctxpp, CUDA, and local-worker CLIs are lower-level fallbacks only when
  `coding-workflow` is unavailable, explicitly out of scope, broken, or itself being debugged.
<!-- coding-workflow:end -->

## Authoritative workflow

- After `coding-workflow` has established the claim, use `todo-orchestrator` as
  the lower-level authority for substantial multi-step coordination when needed.
- SQLite is todo-orchestrator's operational authority.
- `.todo-orchestrator/state.snapshot.json` is versionable recovery state.
- `todos.md` and `todo-status.md` are generated human projections, never synchronization or authority.
- Use the task capsule returned by `todo continue` instead of rereading whole ledgers.
- Preserve unrelated user changes and obey declared scopes, gates, resources, and interlocks.

## Core skill routing

- Within a coding-workflow claim, use `todo-orchestrator` for persistent project
  state, decomposition, concurrency, recovery, gates, and evidence.
- Use `cpp-context-compiler` before broad C++ or CUDA source reads in configured repositories; edit canonical source only.
- Use `cuda` for CUDA correctness, benchmarking, profiling, architecture guidance, and GPU resource-sensitive work.
- Use `local-coding-worker` only for bounded child work authorized by an active todo parent claim; it never owns architecture or task completion.
- Do not route work to removed or archived skills.
