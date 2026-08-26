---
name: todo-orchestrator
description: Transactional orchestration for substantial multi-step projects. Use when Codex should create or continue a persistent task graph, atomically claim safe work across parallel chats, coordinate checkpoints, barriers, interfaces, ownership scopes, locks, resources, gates, evidence, handoffs, or migrate legacy Markdown ledgers.
---

# Todo Orchestrator

## Repository workflow

For substantial repository work, ALWAYS use `coding-workflow` first when it is
available. Claim or resume the authoritative task through `coding-workflow`
before using this skill for bounded orchestration, inspection, testing, or
recovery. Do not directly claim todo work or begin repository mutations first.
Use this lower-level CLI directly only when `coding-workflow` is unavailable,
explicitly out of scope, or itself being debugged.

SQLite is the v2 operational authority.
`.todo-orchestrator/state.snapshot.json` is durable recovery state; Markdown is
a generated projection and legacy migration input. Do not use this skill for a
clearly narrow one-step request.

## Direct fallback: Continue

Use this section only under the direct-CLI exceptions above.

Read repository `AGENTS.md`, resolve this skill's `scripts/todo.py`, then run:

```bash
python <skill-dir>/scripts/todo.py bootstrap --repo-root <repo> --json
python <skill-dir>/scripts/todo.py continue --repo-root <repo> --json
```

Use the returned capsule rather than rereading every ledger. Continue atomically
registers a session, reconciles leases, claims safe ready work, acquires
claim-time locks/resources, and returns the claim token. Preserve that secret.
Proceed without asking the user to choose among safe ready work.

Treat objective, next action, scope, prerequisites, checkpoints, gates,
resources, interlocks, and active siblings as binding. Edit only exclusive
paths; guard uncertain paths. Acquire named locks, lease exclusive resources,
run required gates, pulse long work, inspect changes after pauses, and stop on
invalidated contracts. Never reset, clean, overwrite, or attribute shared
changes without audit.

Bounded local delegation uses `child create`, a restricted child token, and
parent-side evidence acceptance; child output never completes the parent task.

Finish through exactly one structured CLI path: `complete`, `handoff`,
`block`, or `release`. Completion requires valid gates. Checkpoints,
interfaces, barriers, recovery, plans, migration, resources, and cleanup must
use their existing CLI commands; never edit SQLite or projections directly.

For a new empty project, read `references/planning-workflow.md`, validate and
diff a v2 JSON plan, then apply it transactionally. For legacy Markdown,
bootstrap and run `migrate markdown --dry-run` before `--apply`. Expired dirty
claims remain quarantined until explicit recovery.

Live claim replacement is not ordinary recovery. The `recover live-*` path is
reserved for an unchanged, verifiably `coding-workflow`-owned lease and requires
a short-lived one-use approval created manually in an interactive owner terminal.
Never approve it from model context or use it to take over another client's claim.

If a still-live claim token is lost and the claim is not eligible for facade
replacement, an owner may use `recover force-release-inspect`, manually run
interactive `recover force-release-approve`, and then consume the one-use token
with `recover force-release`. This owner-only path requires a clean scope and no
unsafe attached execution. A model must never mint or self-authorize approval.

Hard invariants: do not edit another active claim's paths, cross unopened
barriers, bypass locks or leases, mark work done without gates, auto-clean
state, or treat Markdown/branch separation as coordination authority.

Conditional details and complete preserved procedure:
`references/full-workflow-compatibility.md`. Stable command and data contracts:
`references/cli-reference.md`, `references/v2-architecture.md`,
`references/project-plan-v2.md`, `references/status-and-cleanup.md`, and
`references/todo-format.md`.
