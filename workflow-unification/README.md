# Workflow unification v3

The product has two layers and one ordinary front door: coding-workflow is
protocol v2; todo-orchestrator is its transactional SQLite kernel.
Project-control remains a separate read-only observation plane.
cpp-context-compiler, CUDA, and local-coding-worker remain bounded engines.

## Execution model

A run contains a tree of first-class Codex lanes. The project may be parallel,
but each lane has one role, one ordered queue, at most one active task, and at
most one dispatch. Roles are coordinator, implementer, validator, integrator,
and specialist. Typed messages, lane cursors, decisions, interfaces, and
all/quorum/producer rendezvous coordinate fan-out and fan-in.

Local workers are different: each is a disposable child of one active parent
claim. Its <=4 KiB packet contains only a bounded objective, relevant parent
constraints, a strict subset of paths, exact source references, output schema,
and candidate/acceptance gates. It receives no run charter, lane/sibling brief,
message board, architectural authority, or rendezvous role. The parent accepts,
rejects, integrates, validates, and publishes its candidate result. Child
success never completes the parent.

First-class context is versioned as run charter, lane brief, task brief,
decision ledger, delta inbox, and source references. Normal task/coordination
responses target 8 KiB. Contract changes invalidate only affected fragments.

Same-worktree ownership stays exclusive. Overlapping first-class edits require
declared isolated workspaces from one base commit, immutable artifacts, an
integrator-owned destination, an integration queue, and post-merge gates. Dirty
or conflicted worktrees are preserved. Child writable work normally keeps the
subordinate scope-lease and parent acceptance model.

Use the six protocol tools for normal work, the explicit repository migration
for cutover, and `coding-workflow-admin recover` for owner recovery. Legacy v2
plans normalize to one compatibility run/serial lane; existing snapshots and
audit history remain readable.
