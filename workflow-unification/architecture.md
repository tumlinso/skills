# Workflow Unification v3 Architecture

## Product boundary

Workflow Unification is one product with two layers:

1. **coding-workflow** is the only ordinary model-facing protocol.
2. **todo-orchestrator** is the transactional kernel, owner-maintenance interface, and semantic authority underneath it.

Project-control remains a separate, stateless, strictly read-only observation plane. cpp-context-compiler, CUDA, and local-coding-worker remain separate specialized execution engines invoked or authorized through coding-workflow. They do not become orchestration authorities.

SQLite remains the live authority. Every semantic mutation uses the existing `Database.mutate`/`Service.mutate` transaction and revision/event machinery. Forward-only migrations extend the current schema. Deterministic snapshots and generated Markdown remain recovery and projection products, never synchronization inputs.

## Execution hierarchy

```text
Run
  -> first-class Codex lane tree
       -> one serial task queue per lane
            -> optional bounded local-worker child executions
```

A first-class lane is durable run state assigned to a Codex/project session. It has a role, ordered queue, at most one active task and dispatch, a context cursor, optional managed workspace, and rendezvous obligations. Different lanes may proceed concurrently when dependencies, interfaces, scopes, locks, resources, roles, and workspaces permit it.

A local-worker child remains a disposable bounded subordinate of exactly one active parent claim. It receives a strict subset of parent scope and context, returns a candidate result, and never receives a run role, lane, independent claim, run inbox, decision authority, interface publication authority, rendezvous membership, integration role, or parent-completion authority. The parent Codex lane is the communication and acceptance airlock.

## Canonical package

Canonical workflow code lives under `todo_orchestrator.workflow`:

```text
workflow/
  __init__.py
  foundation.py
  protocol.py
  service.py
  capabilities.py
  roles.py
  runs.py
  lanes.py
  messages.py
  rendezvous.py
  context_fragments.py
  workspaces.py
  recovery.py
  admin.py
  adapters/
    ctxpp.py
    local_worker.py
    cuda.py
  mcp/
    server.py
```

`WorkflowKernel` is the canonical in-process application service. It composes the existing todo `Service`; it does not own a database or transaction engine. The todo CLI and MCP handlers call the same semantic methods. Claim, completion, checkpoint, gate, scheduling, recovery, resource, lock, and interface behavior must not be reimplemented in the MCP layer.

The existing `integrations/coding-workflow-mcp` directory becomes an installer, entry-point shim, migration utility, compatibility tests, and rollback artifact only. Its subprocess todo backend and independent capability semantics are retired after canonical integration passes.

## Durable state additions

Forward-only migrations add normalized tables for:

- runs and immutable/versioned run charters;
- lanes, lane hierarchy, lane task ordering, roles, and context cursors;
- dispatches bound to existing first-class sessions, claims, process identity, heartbeat, context version, and optional workspace;
- hash-stored workflow capabilities with project/repository/session/claim/run/lane/role/task/incarnation lineage and allowed operations;
- bounded typed run messages, recipients, receipts, linked questions/answers, and durable decision/interface references;
- rendezvous, participants, arrival contracts, and idempotent arrivals layered on the existing barrier readiness authority;
- versioned hashed context fragments and targeted invalidations;
- managed first-class workspaces, immutable patch/commit artifacts, integration queues, conflicts, merge results, and cleanup eligibility.

Existing child execution, child attempt, and child scope lease tables remain the only representation of local-worker children. No lane foreign key is added to make a child a peer participant. Child results may reference their parent task/claim and candidate artifacts only.

## Roles

Roles are server-assigned and server-enforced:

- **coordinator** manages first-class lane topology, roles, structured plan proposals, rendezvous, decisions, questions, and integration requests within project constraints.
- **implementer** mutates assigned scopes, publishes task-owned artifacts/interfaces, communicates, arrives, and finishes its assigned work.
- **validator** is read/gate oriented and mutates only declared validation artifacts.
- **integrator** exclusively owns the destination integration workspace, merge queue, conflicts, post-merge gates, and final integrated artifact.
- **specialist** is a durable first-class Codex lane only when explicitly planned; it is still broader than a local-worker child.

Role authority never bypasses task scope, dependencies, locks, leases, resources, interfaces, workspace ownership, or gates.

## Communication and fan-in

Run communication is bounded typed state, not a shared transcript. Supported kinds are status, question, answer, decision, interface_change, conflict, artifact, handoff, and rendezvous_arrival. Recipients are lanes, roles, tasks, or the run. Per-lane receipts/cursors make `sync` return unread relevant deltas only. Answers resolve linked questions transactionally. Decisions and interface changes update their existing durable authorities.

Local-worker findings use child-only result kinds: candidate_patch, test_result, performance_measurement, source_finding, review_finding, and diagnostic_finding. They enter run state only after parent collection, validation, explicit acceptance or rejection, and optional parent publication.

Rendezvous support all-participant, quorum, and designated-producer modes. Arrivals are idempotent per first-class lane and include bounded source, artifact, interface, gate, evidence, warning, and context provenance. Satisfaction atomically opens the existing declarative join/integration task. A local child cannot arrive and child success cannot satisfy fan-in.

## Context contract

Durable context is fragmentary and versioned: run charter, lane brief, task brief, decision ledger, delta inbox, and source packet references. Each fragment has kind, owner scope, version, content hash, creation revision, and invalidation/supersession state.

Normal output budgets are approximately 8 KiB for `next_task`, `coordinate_task`, and `finish_task`, and 4 KiB for delegation results. `inspect_task` expands only an explicit bounded target. Relevant fragment changes return `context_stale` plus references rather than replaying the project.

Local-child packets deliberately exclude the run charter, lane brief, sibling context, run inbox, unrelated decisions, and rendezvous state. They contain only objective, relevant parent constraints, strict child paths, exact source packet, output schema, candidate gates, acceptance gates, and minimum interface facts.

## Workspace safety

Default mutation mode is same-worktree exclusive ownership. `read_shared`, `isolated_merge`, and `contract_split` are explicit alternatives. Overlapping first-class edits require separately managed worktrees from the same base, immutable commit/patch artifacts, a designated integrator and task, an exclusively owned destination, and post-merge gates. Conflicts become explicit integration work. Dirty or conflicted worktrees are never automatically deleted.

Local children keep child scope leases by default. Any child sandbox is disposable and parent-controlled, produces only a candidate artifact, and never becomes a lane workspace or independent integration participant.

## Recovery and compatibility

The owner operation is `coding-workflow-admin recover --repo <repo> [--task <id>] --reason <reason>`. It requires interactive input/output, obtains a project recovery lock, inspects every live authority and process, prints a bounded plan, requires exact confirmation, preserves files and artifacts, refuses demonstrably live mutation, records sanitized audit, and is idempotent.

First-class recovery may reissue capabilities, resume/reassign dispatches, and preserve managed workspaces and run obligations. Dead local children instead become terminal attempts, preserve candidates, release child scope, and return control to the parent. They do not create orphan lanes or project-wide deadlock.

Plan schema v2 remains accepted and normalizes to one compatibility run with one serial lane. New declarative run/lane/rendezvous/workspace entities use a separate later plan schema. Database migration, plan schema, protocol, and snapshot versions remain distinct. Legacy repositories without `workflow_front_door = "coding-workflow"` retain compatibility; migrated repositories reject ordinary direct automated mutations with `workflow_front_door_required` while preserving read-only commands, interactive maintenance, tests, and explicit self-debugging.

## Integration ownership

The kernel foundation freezes `WFU-KERNEL-CONTRACT-V1`. Only after that checkpoint may the six core lanes edit their disjoint modules in separate worktrees. `WFU-20` alone owns shared service/CLI dispatch, migrations integration, plan normalization, snapshots, projections, semantic reads, and package registries. `WFU-21` owns routing, shim, installer, migration, and documentation after integration. `WFU-22` owns only the separate project-control read-side branch. `WFU-30` validates in disposable repositories. `WFU-31` alone owns real cutover.
