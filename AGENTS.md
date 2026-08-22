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
- `local-coding-worker` is introduced by CORE4 and must not be invoked until its software-ready checkpoint exists.
- Do not route work to removed or archived skills.
