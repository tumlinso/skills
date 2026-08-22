# Repo Guidance

## Authoritative workflow

- For substantial multi-step work, use `todo-orchestrator`.
- SQLite is todo-orchestrator's operational authority.
- `.todo-orchestrator/state.snapshot.json` is versionable recovery state.
- `todos.md` and `todo-status.md` are generated human projections, never synchronization or authority.
- Use the task capsule returned by `todo continue` instead of rereading whole ledgers.
- Preserve unrelated user changes and obey declared scopes, gates, resources, and interlocks.

## Core skill routing

- Use `todo-orchestrator` for persistent project state, decomposition, concurrency, recovery, gates, and evidence.
- Use `cpp-context-compiler` before broad C++ or CUDA source reads in configured repositories; edit canonical source only.
- Use `cuda` for CUDA correctness, benchmarking, profiling, architecture guidance, and GPU resource-sensitive work.
- Use `local-coding-worker` only for bounded child work authorized by an active todo parent claim; it never owns architecture or task completion.
- Do not route work to removed or archived skills.
