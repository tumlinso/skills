---
name: local-coding-worker
description: Delegate bounded, todo-authorized coding investigations to a local backend using ctxpp packets and isolated source state. Use for explicitly delegated explain, debug, review, or test-planning work when a parent todo claim supplies a child token. The CORE4 read-only MVP never edits source, commits, pushes, chooses architecture, or starts recursive agents.
---

# Local Coding Worker

Use this skill only from an active todo-orchestrator parent claim. The parent
creates the child execution and retains task, gate, and acceptance authority.

## Read-only workflow

1. Create a bounded `LCW-REQUEST/1` JSON document using the schema in
   `schemas/delegation-spec-v1.schema.json`.
2. Run `python scripts/local_worker.py eligible --request REQUEST.json`.
3. If eligible, run `python scripts/local_worker.py run --request REQUEST.json`.
4. Treat `needs_codex` as a successful escalation, not a worker failure.
5. Use only the compact result. Canonical source and todo SQLite remain
   authoritative.

The controller heartbeats the restricted child token, asks ctxpp for one
bounded packet, copies only declared scopes into temporary read-only state,
invokes one backend, normalizes the result, and reports the child outcome.

Read `references/read-only-contract.md` before changing controller roles,
eligibility, authorization, isolation, or result semantics.

## Hard limits

- Allow only `explain`, `debug`, `review`, and `test_plan` roles.
- Never accept writable mode, changed paths, shell strings, recursive agents,
  architecture decisions, commits, pushes, or parent lifecycle actions.
- Never expose the child token in output or telemetry.
- Do not download or install a backend. The MVP supports `fake` only.
