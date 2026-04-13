---
name: todo-orchestrator
description: Standalone orchestration skill for substantial multi-step work that needs deep planning, a persistent `todos.md` ledger, a legible `todo-status.md` pickup register, runtime discovery of relevant repo-local skills and reference files, and non-interactive execution after planning. Use when Codex should plan with the user, write and maintain `todos.md`, resume from an existing ledger, coordinate concurrent workstreams, surface delegation-ready substreams, or keep working through a repo task until it is done. Use `todo-cleanup` only for explicit post-completion cleanup of finished workstream ledgers. Do not use this skill for narrow one-off tasks that already clearly belong to a more specialized skill.
---

# Todo Orchestrator

Use this skill as the orchestration layer for substantial work.

This skill is responsible for:

- building a strong plan with the user when the task is substantial, ambiguous, or multi-step
- writing that plan into `todos.md`
- treating `todos.md` as the canonical execution ledger
- keeping `todo-status.md` as the quick pickup register for parallel or resumable work
- supporting concurrent work through workstream files under `todos/`
- discovering relevant repo-local skills and reference files at runtime
- continuing implementation non-interactively after planning unless truly blocked

Do not let this skill steal obvious one-off work from a better specialized skill. If the task is already narrow and a specialized skill is clearly the best fit, use that specialized skill directly instead of wrapping it in orchestration.

## Trigger Boundary

Use this skill when the user is asking for any of:

- "plan this with me and then execute it"
- "turn this rough idea into a task plan and work through it"
- "keep working through this repo task using `todos.md`"
- "resume the current plan from `todos.md`"
- "organize this work and keep going until it is done"
- substantial multi-step repo work where a persistent plan or concurrent workstreams would prevent drift

Do not use this skill when the task is primarily:

- a simple one-step fix
- a narrow request that already clearly belongs to a specialized skill
- purely conversational brainstorming with no intent to turn it into execution

## Startup

Before proposing a plan or making implementation decisions:

1. Inspect the repo context first.
2. Read repo-level `AGENTS.md` if present.
3. Read root `todos.md` if present.
4. Read `todo-status.md` if present to see pickup-ready, claimed, idle, and completed workstreams.
5. Inspect `todos/` for active workstream ledgers if present.
6. Discover available repo-local skills dynamically.
7. Discover useful repo-local reference files dynamically.
8. Determine whether there is already an active plan that should be resumed instead of replaced.

Prefer the helper scripts when they are available:

```bash
python todo-orchestrator/scripts/discover_skills_and_refs.py --repo-root <repo-root> --task "<task>"
python todo-orchestrator/scripts/summarize_todos.py --repo-root <repo-root>
python todo-orchestrator/scripts/cleanup_todos.py --repo-root <repo-root> --dry-run
```

Do not hardcode companion skill names into your working method. Discover them from the repo at runtime and record the relevant ones in the ledger.

## Planning

When the work is substantial, ambiguous, or multi-step:

1. Read `references/planning-workflow.md`.
2. Plan with the user in depth before implementation.
3. Challenge weak assumptions when that improves the plan.
4. Turn fuzzy goals into concrete steps, validation, and done criteria.
5. Identify likely relevant repo-local skills and reference files.
6. Split the work into domain-based workstreams when that creates clear ownership or enables parallel pickup.
7. Tell the user which workstreams are good delegation candidates and which must remain serial.
8. Write the resulting plan into the ledger.
9. Ensure repo-level `AGENTS.md` contains the durable reminders to consult `todos.md`.

Use:

```bash
python todo-orchestrator/scripts/init_todos.py --repo-root <repo-root> --objective "<objective>"
python todo-orchestrator/scripts/update_todos.py --repo-root <repo-root> --workstream <slug> ...
```

When assumptions, progress notes, or pickup context contain markdown or shell-sensitive text such as backticks or globs, prefer the structured payload path instead of raw shell arguments:

```bash
python todo-orchestrator/scripts/update_todos.py --repo-root <repo-root> --payload-file - <<'EOF'
{"workstream":"debug-stream","progress_note":["Preserve `code` and `*.globs` exactly."]}
EOF
```

Planning outputs must include:

- current objective
- a quick-start summary for each workstream that another thread can pick up without prior context
- the exact repo-local skills and reference files that a fresh thread must read before starting each workstream
- planning notes
- assumptions
- task list
- blockers
- suggested skills
- useful reference files
- progress notes
- next actions
- done criteria

For concurrent work, use:

- root `todos.md` as the canonical index and shared-status ledger
- `todo-status.md` as the legible pickup register
- `todos/<workstream>.md` for detailed execution of each active stream

If a workstream already exists, preserve and extend it instead of replacing it.

When splitting into workstreams:

- keep each workstream narrow enough that a fresh thread can own it without rediscovering the entire repo
- put the domain boundary and handoff context near the top of the workstream file
- name the exact skills and references to load in the quick-start block, not just later in the full ledger
- mark streams that are good delegation targets in `todo-status.md`

## Execution

After planning is complete:

1. Read `todos.md` before continuing work.
2. Read `todo-status.md` before claiming or starting a parallel workstream.
3. If the relevant workstream exists under `todos/`, read that file too.
4. Use the recorded plan as the active source of truth.
5. Keep task states, assumptions, blockers, suggested skills, useful references, progress notes, and next actions current as implementation proceeds.
6. Prefer a specialized repo-local skill when runtime discovery shows it is a better fit for the next step.
7. Continue until the task is actually complete.

The implementation ledger must stay current enough that another agent can resume from it without rediscovering context.

Execution-state rules:

- `planned` + `ready`: not started and safe to pick up
- `in_progress` + `claimed`: currently being written; choose another stream
- `in_progress` + `idle`: incomplete but resumable; safe to pick up
- `blocked`: not pickable until the blocker is cleared
- `done` + `closed`: finished and eligible for cleanup review

If the user does not delegate parallelizable work, continue through the workstreams serially yourself. If a stream is `ready` or `idle` and not already claimed elsewhere, pick it up and keep going instead of waiting for another thread. If `todo-status.md` shows another agent already claimed a stream, skip it and choose a different ready or idle stream.

## Non-Interactive Implementation

Default to non-interactive execution once planning is complete.

Do not stop after each milestone. Do not repeatedly ask what to do next if `todos.md` already makes the next step clear.

Before asking the user for input, check whether any stream is still actionable. If a workstream is `ready` or `idle` and not already claimed by another thread, claim it and continue. Ask only when no stream can be advanced without one of the true blockers below.

Make reasonable assumptions and record them in the ledger. Ask for guidance only when truly blocked by:

- missing credentials or access
- destructive or irreversible actions
- ambiguity severe enough that substantial work would likely be wasted

If blocked, update `Blockers`, `Assumptions`, and `Next Actions` before asking.

If a thread stops work without finishing:

- release the stream from `claimed` to `idle`
- leave a short next action in `todo-status.md`
- make sure the workstream file is still sufficient for a fresh pickup

## Ledger Rules

Follow `references/todo-format.md` for the default layout.

Use root `todos.md` as the canonical top-level ledger. For concurrent work:

- keep shared assumptions and top-level status in root `todos.md`
- keep quick pickup state in `todo-status.md`
- keep detailed execution in `todos/<workstream>.md`
- keep the root `Workstreams` section synchronized with per-workstream status

Use `todo-status.md` to distinguish work that is merely unfinished from work that is actively being written. Another thread should be able to read that file and decide what to pick up next without additional context.

`todo-cleanup` is explicit cleanup mode:

- only use it when the user explicitly asks for cleanup
- it may report when cleanup is safe once every tracked workstream is `done`
- it must not run automatically
- it deletes completed workstream ledgers and compacts the root ledgers after completion

Do not overwrite user-written planning notes carelessly. Preserve unmanaged text where possible and update the managed structured sections in place.

## Reference Map

- `references/planning-workflow.md`: how to do deep collaborative planning before execution
- `references/todo-format.md`: stable markdown layout for root and workstream ledgers
- `references/status-and-cleanup.md`: pickup register semantics, claiming rules, and explicit cleanup behavior
- `references/execution-rules.md`: implementation-mode rules for non-interactive execution
- `references/examples.md`: request shapes that should or should not trigger this skill

## Helper Scripts

- `scripts/init_todos.py`: initialize root `todos.md`, create `todos/`, and optionally create a workstream ledger
- `scripts/update_todos.py`: update structured sections, task states, blockers, assumptions, suggested skills, useful references, and next actions; use `--payload-file -` for shell-sensitive text
- `scripts/summarize_todos.py`: emit a concise summary of active workstreams, blockers, and next actions
- `scripts/cleanup_todos.py`: verify every workstream is done, then explicitly remove completed ledgers and compact the root files
- `scripts/discover_skills_and_refs.py`: inspect the repo for candidate skills and likely-useful reference files

If the repo already has stronger utilities for these jobs, use them instead of duplicating behavior.

## Hard Rules

- Do not hardcode a fixed list of helper skills into the orchestration method.
- Do not stop after writing a plan unless the task was explicitly planning-only.
- Do not replace a clearly better specialized skill when one is available.
- Do not keep interrupting implementation for confirmation when the ledger already makes the next step clear.
- Do not replace existing user planning notes when an additive update is enough.
- Do not treat `in_progress` alone as proof that another thread is actively writing; check `todo-status.md`.
- Do not run `todo-cleanup` automatically.
