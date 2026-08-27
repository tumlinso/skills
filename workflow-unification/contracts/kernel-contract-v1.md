# WFU Kernel Contract v1

Checkpoint: `WFU-KERNEL-CONTRACT-V1`

This contract freezes the database and service seams consumed by WFU-10 through WFU-15. Core lanes may implement only against these entities and `todo_orchestrator.workflow.foundation`; shared dispatch and compatibility integration remains WFU-20-owned.

## Version separation

- Database migration version: `10`
- Preserved project/on-disk schema value: `2`
- Accepted legacy plan schema: `2`
- New workflow plan schema target: `3`
- Workflow snapshot section target: `1`
- Model-facing protocol version: `2`

Historical migrations 1 through 9 are unchanged. Migration 10 is forward-only, serialized by the existing `BEGIN IMMEDIATE` initialization transaction, and rolls back as a unit on failure.

## Transaction boundary

Workflow modules receive the existing todo database/service through dependency injection. A semantic write is an operation passed to `Database.mutate`, which allocates one project revision and appends one bounded event in the same transaction. Modules must not open a separate writable authority, independently update project revision, or write projections.

Reads use `Database.read`. WFU-20 owns deterministic export/snapshot/restore/projection registration and normalized semantic reads for the new tables.

## First-class run entities

- `workflow_runs`: run lifecycle and root task.
- `workflow_run_charters`: immutable version/hash/revision charter history.
- `workflow_lanes`: run tree, server-enforced role, context cursor, workspace mode.
- `workflow_lane_tasks`: ordered serial queue. A partial unique index permits at most one active task per lane.
- `workflow_dispatches`: existing session + claim assignment, context version, process identity, heartbeat, optional managed workspace. Partial unique indexes permit at most one active dispatch per lane and session.

First-class roles are coordinator, implementer, validator, integrator, and specialist. Local-worker children remain in existing `child_executions`, `child_attempts`, and `child_scope_leases`; none of those tables gains run, lane, role, or dispatch columns.

## Capability lineage

`workflow_capabilities` stores hashes only and distinguishes `first_class` from `child` with database checks.

A first-class record requires project UUID, repository identity, existing session, claim, run, lane, role, task, operations, expiry, and incarnation. A child record requires a parent capability and existing child execution, has no run/lane/role, and remains under the parent project/repository/claim/task lineage. Higher-level validation rechecks authoritative state and enforces operation subset and the prohibition on run-level actions.

XDG state may locate a project database but is never authoritative.

## Communication and rendezvous

- `workflow_messages`, recipients, and receipts implement bounded typed run messages and lane cursors.
- Message kinds are status, question, answer, decision, interface_change, conflict, artifact, handoff, and rendezvous_arrival.
- `workflow_rendezvous`, participants, and arrivals implement all, quorum, and producer modes while optionally binding the existing barrier authority.
- Participants and arrivals foreign-key only to `workflow_lanes`. There is no child participant column.
- Join readiness and barrier changes occur in one WFU-11/WFU-20-composed transaction.

## Context

`workflow_context_fragments` stores immutable versions and hashes for run_charter, lane_brief, task_brief, decision_ledger, delta_inbox, and source_packet_ref, with targeted invalidation/supersession metadata.

Frozen budgets from `foundation.py` are 8 KiB for next/coordinate/finish, 4 KiB for delegation results and child packets, and 4 KiB per message payload. Canonical JSON hashing is stable and secret-free.

## Workspaces and integration

- `workflow_workspaces` tracks repository, run, lane, mode, base, path, branch, state, artifact, diff, merge result, integration task, and cleanup eligibility.
- `workflow_patch_artifacts` stores immutable commit/patch references and hashes.
- `workflow_integration_queue` serializes artifacts under an integrator lane and explicit integration task.

Workspace modes are exclusive, read_shared, isolated_merge, and contract_split. Semantic scopes remain scheduling hints; workspace isolation is mutation safety; integration gates are correctness authority.

## Parent-mediated child results

`workflow_child_result_candidates` stores bounded candidate_patch, test_result, performance_measurement, source_finding, review_finding, and diagnostic_finding records. Each references an existing child execution and parent claim, but never a run, lane, rendezvous, or message. Parent acceptance/rejection and optional publication are higher-level WFU-15/WFU-20 operations.

## Recovery audit

`workflow_recovery_audit` records sanitized proposed and executed owner recovery plans. Existing recovery history tables remain untouched. WFU-14 composes live-state inspection and refusal; WFU-20 routes deprecated wrappers into that engine.

## Core ownership

- WFU-10: roles.py, runs.py, lanes.py
- WFU-11: messages.py, rendezvous.py
- WFU-12: context_fragments.py
- WFU-13: workspaces.py
- WFU-14: recovery.py, admin.py
- WFU-15: protocol.py, capabilities.py, adapters/, mcp/

Core lanes do not edit migrations.py, service.py, commands, plans, schemas, snapshots, projections, semantic reads, package exports, the compatibility shim, installer, or shared registries. Those are integration-owned.
