# Repo Guidance

<!-- coding-workflow:start -->
## Coding workflow

For substantial repository work, use `coding-workflow`.
Do not directly invoke todo-orchestrator, cpp-context-compiler, CUDA, or
local-coding-worker unless coding-workflow returns an explicit bounded fallback
authorization, the user explicitly requests maintenance, or coding-workflow
itself is being debugged.

Start with `next_task`. Use `inspect_task` for bounded context,
`coordinate_task` for typed coordination, optional `delegate_task` only for a
bounded subordinate child, `collect_delegation` only for its returned handle,
and `finish_task` for every first-class task disposition. Never poll local
delegation; `local_unavailable` and `not_eligible` mean continue directly.

First-class Codex agents form a parallel tree of serial run lanes with enforced
roles. Local workers are disposable children of exactly one active parent
claim. They never claim project todos, receive lanes or roles, communicate
across lanes, join rendezvous, publish decisions or interfaces, or complete the
parent task.
<!-- coding-workflow:end -->

## State and specialized engines

- Todo SQLite is the workflow kernel's semantic authority.
- `.todo-orchestrator/state.snapshot.json` is deterministic recovery state.
- `todos.md`, `todo-status.md`, and `todos/*.md` are generated projections, not synchronization authority.
- Project-control is a separate, strictly read-only observation plane.
- cpp-context-compiler, CUDA, and local-coding-worker remain bounded execution engines authorized by coding-workflow.
- Preserve unrelated changes and obey scopes, interfaces, gates, locks, resources, workspaces, and rendezvous.
