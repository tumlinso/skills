# Kernel State and Implementation Seams

## Existing authorities reused

- `todo_orchestrator.db.Database` owns connections, migration serialization, transactions, revision increments, and event append.
- `todo_orchestrator.service.Service` remains the semantic facade used by CLI and composed by `WorkflowKernel`.
- Existing claims, sessions, gates, resources, locks, interfaces, decisions, barriers, checkpoints, completion provenance, child executions, audit, projections, and semantic reads remain authoritative.
- Existing `validate_acyclic` remains plan-time dependency-cycle validation and is extended by normalized runtime wait diagnostics.

No new module opens a competing writable database. New services accept `Service`, `Database`, clock, process probe, Git runner, and adapter dependencies explicitly for tests.

## Foundation contract inputs

`WFU-02` defines forward-only tables, indexes, foreign keys, enums, serialization limits, stable record mappers, and fixtures. It also defines a narrow transaction-bound repository interface consumed by WFU-10 through WFU-15. Core lanes must not edit migrations, shared service dispatch, projections, snapshots, CLI registries, or package registries.

At minimum, database constraints enforce one active dispatch and one active task per lane, unique lane order positions, idempotent message receipts, one arrival per lane/rendezvous, immutable fragment version/hash identity, and one active capability incarnation per lineage as appropriate.

Volatile raw capability material, session secrets, and live leases are excluded from durable tracked snapshots. Durable run, lane, message, rendezvous, fragment, workspace, patch, and audit semantics are exported/restored deterministically.

## Core module ownership

| Task | Exclusive modules | Shared integration deferred to WFU-20 |
| --- | --- | --- |
| WFU-10 | roles.py, runs.py, lanes.py | Service/CLI scheduling dispatch and plan normalization |
| WFU-11 | messages.py, rendezvous.py | existing barrier/interface/decision wiring |
| WFU-12 | context_fragments.py | next/inspect/coordinate capsule composition |
| WFU-13 | workspaces.py | CLI registration, snapshot/projection integration |
| WFU-14 | recovery.py, admin.py | deprecated wrapper dispatch and installed entry point |
| WFU-15 | protocol.py, capabilities.py, adapters/, mcp/ | package exports, compatibility shim, installer |

Each lane supplies focused tests in its owned test file. Shared end-to-end tests and compatibility changes belong to WFU-20 or later.

## Specialized adapters

Adapters use fixed shell-free argv and bounded JSON contracts. ctxpp remains the source-packet authority; CUDA remains lazy and resource-aware; local-worker remains admission-driven and subordinate. Adapter imports have no process, repository, network, GPU, or model side effects.

## Project-control read contract

Todo publishes one additive normalized semantic read after integration. Project-control consumes that command rather than interpreting raw workflow tables. Absence of the new read degrades to explicit partial legacy output. First-class sessions/dispatches and subordinate local children remain separate normalized collections. The existing eight tools and all mutation sentinels remain unchanged.
