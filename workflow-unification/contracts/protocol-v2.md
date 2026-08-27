# Coding-Workflow Protocol v2

## Discovery

The ordinary MCP server exposes exactly six tools:

1. `next_task`
2. `inspect_task`
3. `coordinate_task`
4. `delegate_task`
5. `collect_delegation`
6. `finish_task`

`run_gates` becomes `coordinate_task(action="run_gates")`. Terminal checkpoint repair becomes automatic reconciliation and owner recovery. Recovery approval is absent from `next_task`.

## Common response envelope

Where applicable every response contains `protocol_version: 2`, stable `status`, run identity, lane identity and role, task identity, context versions/cursor, `allowed_actions`, `recommended_next_call`, and compact blockers/warnings. Stable statuses are `claimed`, `resumed`, `idle`, `blocked`, `attention_required`, `context_stale`, `recovery_needed`, and `fallback_authorized`.

`fallback_authorized` names the specialized skill, operation, reason, bounded scope, and read/write mode. It never carries a raw token.

Normal responses are bounded to about 8 KiB; delegation results are about 4 KiB. Safety state is referenced, never silently truncated.

## Operations

`next_task` atomically bootstraps/resolves the project, registers or resumes a first-class Codex session, resolves the active or compatibility run, resumes or safely assigns a lane and server-selected role, claims the lane's current task, acquires claim-time leases, reissues a lineage-valid opaque capability, and returns compact run/lane/task/delta fragments. Local children never call it.

`inspect_task` is read-only, budgeted, scope-aware, and supports task, source, evidence, run, lane, decision, messages, rendezvous, workspace, and integration state. C++/CUDA source expansion uses cpp-context-compiler when configured. Child packets are produced separately and cannot use this full surface.

`coordinate_task` accepts only validated typed actions: sync, fork, message, answer, arrive, publish_interface, run_gates, request_integration, accept_child, and reject_child. Role, capability class, task scope, and action schema are enforced server-side. Child capabilities cannot call run-level actions.

`delegate_task` derives a restricted child capability from exactly one active parent claim and returns immediately on unavailable/not-eligible. It supplies only the bounded child packet and never waits or promotes the child.

`collect_delegation` is nonblocking and idempotent where possible. Collection produces a candidate subordinate result only. Parent acceptance or rejection is explicit.

`finish_task` supports complete, handoff, block, and release. Completion atomically validates/runs required gates, freezes gate provenance, records artifacts, publishes eligible task-owned checkpoints/interfaces, records handoff, advances the serial lane, submits configured first-class arrivals, and releases claims, leases, locks, resources, and capabilities. Child completion never invokes it for the parent.

## Authorization

Model-facing handles are opaque. Hash-stored capability records bind project UUID, canonical repository identity, session, claim, run, lane, role, task, operations, expiry, and incarnation. Every use revalidates authoritative todo state. A disposable XDG locator may locate the project database but carries no independent semantics.

First-class and child capabilities are distinct classes. A child capability is derived from exactly one parent and cannot be exchanged for a claim, lane, role, run message, rendezvous arrival, decision, interface publication, or parent completion.
