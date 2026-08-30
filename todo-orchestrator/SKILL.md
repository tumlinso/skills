---
name: todo-orchestrator
description: Internal transactional kernel and owner maintenance interface beneath Project Control. Use directly only for explicit maintenance, debugging, plan administration, recovery, or when Project Control provides bounded fallback authorization. It is not the ordinary model-facing workflow.
---

# Todo Orchestrator Kernel

## Routing

For substantial repository work, use the `project-control` Codex profile.
Todo-orchestrator is the SQLite-backed transactional kernel used in-process by
that profile, not a second front door. Do not directly claim or mutate a
migrated repository unless the user explicitly requests maintenance, Project
Control is being debugged, or Project Control returns a bounded fallback
authorization.

Read-only status, explain, audit, doctor, export, and semantic reads remain
available. Legacy repositories without `workflow_front_door` retain v2 CLI
compatibility. New and newly canonicalized repositories use
`workflow_front_door = "project-control"` and return
`workflow_front_door_required` for ordinary noninteractive direct mutations.
The historical `coding-workflow` value remains accepted during the bounded
compatibility window; it is not a second ordinary front door or live server.
Interactive owner maintenance and explicit in-process self-debug/test modes
remain possible; neither uses a model-held fallback secret.

## Authority

SQLite is live semantic authority. `.todo-orchestrator/state.snapshot.json` is
deterministic durable recovery state. Markdown todo files are generated human
projections and legacy migration inputs only. Every semantic mutation remains a
revisioned transaction with append-only event history.

First-class runs, serial lanes, roles, dispatches, messages, rendezvous,
context fragments, managed workspaces, and integration queues describe Codex
project agents. Existing child executions remain bounded subordinate work under
one active parent claim. A child cannot claim a todo, receive a lane or role,
message another lane, publish a decision/interface, arrive at a rendezvous, or
complete its parent.

## Explicit maintenance and debugging

Use the stable CLI only within an explicit maintenance/debugging boundary:

```bash
python <skill-dir>/scripts/todo.py status --repo-root <repo> --json
python <skill-dir>/scripts/todo.py semantic state --repo-root <repo> --json
python <skill-dir>/scripts/todo.py doctor --repo-root <repo> --json
```

For an unmigrated legacy project or an explicitly authorized workflow
self-debugging session, `bootstrap`, `continue`, plan administration, gates,
and lifecycle commands keep their v2 contracts. Preserve returned tokens
privately. Never edit SQLite or generated projections manually.

Owner recovery is one installed operation:

```bash
project-control admin recover --repo <repo> [--task <id>] --reason "<reason>"
```

It requires a TTY, prints a bounded plan, requires exact confirmation, refuses
live mutable work, preserves dirty files/workspaces/patches, and records
sanitized audit evidence. `--inspect-only` is non-mutating. Deprecated live
override, force release, and terminal checkpoint commands are maintenance-only
compatibility wrappers and are not normal model operations.

## Invariants

- Never bypass task scopes, interfaces, gates, locks, resources, or recovery refusal.
- Never expose todo/session/child/resource/recovery tokens to a model.
- Never treat child success as parent completion.
- Never reset, clean, delete, or overwrite user files to release workflow state.
- Never use Markdown, branch separation, or symbol-level scope as mutation authority.

Read [workflow v3 operations](references/workflow-v3-operations.md) for the
canonical product model. Read [maintenance compatibility](references/maintenance-compatibility.md)
only for legacy CLI and deprecated wrapper details. Stable historical v2 data
contracts remain documented in `references/`.
