---
name: local-coding-worker
description: Delegate bounded, todo-authorized read-only or scoped writable coding work to a local backend using ctxpp packets and isolated source state. Use only when an active parent todo claim authorizes a child execution. Never use it for architecture, task ownership, commits, pushes, or recursive agents.
---

# Local Coding Worker

Use this skill only from an active todo parent claim. The parent retains task,
gate, acceptance, commit, and push authority.

## Workflow

1. Let the parent create a bounded child execution and restricted token.
2. For read-only investigation, validate and run an `LCW-REQUEST/1` with
   `scripts/local_worker.py eligible|run`.
3. For the complete fake-backend flow, run `scripts/local_worker.py integrate`
   with a `CORE4-INTEGRATION-REQUEST/1`.
4. Treat `needs_codex` as a successful hand-back. Use only the compact result.

Read [read-only-contract](references/read-only-contract.md) for read-only role
or packet changes, [writable-work-contract](references/writable-work-contract.md)
for patch/acceptance changes, and [integration-contract](references/integration-contract.md)
for the complete flow.

Read `references/read-only-contract.md` before changing controller roles,
eligibility, authorization, isolation, or result semantics.

## Hard limits

- Allow only `explain`, `debug`, `review`, and `test_plan` roles.
- Writable work requires declared child scopes, isolated source state, external
  verification, and guarded parent-side acceptance.
- Never accept shell strings, recursive agents, architecture decisions,
  commits, pushes, scope expansion, or parent lifecycle actions.
- Never expose the child token in output or telemetry.
- Do not download or install a backend or model. Until real assets are approved,
  use the deterministic fake backend only.
