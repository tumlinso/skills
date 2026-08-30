# Repo Guidance

<!-- project-control:start -->
## Project Control workflow

For substantial repository work, use the `project-control` Codex profile.
Do not directly invoke todo-orchestrator, cpp-context-compiler, CUDA, or
local-coding-worker unless Project Control returns an explicit bounded fallback
authorization, the user explicitly requests maintenance, or Project Control
itself is being debugged.

Start with `next_task`. Use `inspect_task` for bounded context,
`coordinate_task` for typed coordination, optional `delegate_task` only for a
bounded subordinate child, `collect_delegation` only for its returned handle,
and `finish_task` for every first-class task disposition. Never poll local
delegation; `local_unavailable` and `not_eligible` mean continue directly.

Use this cheap-first workflow context before rich reads. Escalate to Project
Control's rich read tools only when bounded task context is insufficient or
source, architecture, history, impact, performance, or cross-project context is
genuinely needed. The old `coding-workflow` name is a temporary compatibility
alias for historical configuration and recovery, not a second ordinary front
door or a second live MCP registration.

First-class Codex agents form a parallel tree of serial run lanes with enforced
roles. Local workers are disposable children of exactly one active parent
claim. They never claim project todos, receive lanes or roles, communicate
across lanes, join rendezvous, publish decisions or interfaces, or complete the
parent task.
<!-- project-control:end -->

## State and specialized engines

- Todo SQLite is the workflow kernel's semantic authority.
- `.todo-orchestrator/state.snapshot.json` is deterministic recovery state.
- `todos.md`, `todo-status.md`, and `todos/*.md` are generated projections, not synchronization authority.
- Project Control's observer profile remains strictly project-read-only; its separate Codex profile owns the six workflow tools.
- cpp-context-compiler, CUDA, and local-coding-worker remain bounded execution engines authorized by Project Control.
- Preserve unrelated changes and obey scopes, interfaces, gates, locks, resources, workspaces, and rendezvous.
