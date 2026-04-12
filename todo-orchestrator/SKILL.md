---
name: todo-orchestrator
description: Standalone orchestration skill for substantial multi-step work that needs deep planning, a persistent `todos.md` ledger, runtime discovery of relevant repo-local skills and reference files, and non-interactive execution after planning. Use when Codex should plan with the user, write and maintain `todos.md`, resume from an existing ledger, coordinate concurrent workstreams, or keep working through a repo task until it is done. Do not use this skill for narrow one-off tasks that already clearly belong to a more specialized skill.
---

# Todo Orchestrator

Use this skill as the orchestration layer for substantial work.

This skill is responsible for:

- building a strong plan with the user when the task is substantial, ambiguous, or multi-step
- writing that plan into `todos.md`
- treating `todos.md` as the canonical execution ledger
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
4. Inspect `todos/` for active workstream ledgers if present.
5. Discover available repo-local skills dynamically.
6. Discover useful repo-local reference files dynamically.
7. Determine whether there is already an active plan that should be resumed instead of replaced.

Prefer the helper scripts when they are available:

```bash
python todo-orchestrator/scripts/discover_skills_and_refs.py --repo-root <repo-root> --task "<task>"
python todo-orchestrator/scripts/summarize_todos.py --repo-root <repo-root>
```

Do not hardcode companion skill names into your working method. Discover them from the repo at runtime and record the relevant ones in the ledger.

## Planning

When the work is substantial, ambiguous, or multi-step:

1. Read `references/planning-workflow.md`.
2. Plan with the user in depth before implementation.
3. Challenge weak assumptions when that improves the plan.
4. Turn fuzzy goals into concrete steps, validation, and done criteria.
5. Identify likely relevant repo-local skills and reference files.
6. Write the resulting plan into the ledger.
7. Ensure repo-level `AGENTS.md` contains the durable reminders to consult `todos.md`.

Use:

```bash
python todo-orchestrator/scripts/init_todos.py --repo-root <repo-root> --objective "<objective>"
python todo-orchestrator/scripts/update_todos.py --repo-root <repo-root> --workstream <slug> ...
```

Planning outputs must include:

- current objective
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
- `todos/<workstream>.md` for detailed execution of each active stream

If a workstream already exists, preserve and extend it instead of replacing it.

## Execution

After planning is complete:

1. Read `todos.md` before continuing work.
2. If the relevant workstream exists under `todos/`, read that file too.
3. Use the recorded plan as the active source of truth.
4. Keep task states, assumptions, blockers, suggested skills, useful references, progress notes, and next actions current as implementation proceeds.
5. Prefer a specialized repo-local skill when runtime discovery shows it is a better fit for the next step.
6. Continue until the task is actually complete.

The implementation ledger must stay current enough that another agent can resume from it without rediscovering context.

## Non-Interactive Implementation

Default to non-interactive execution once planning is complete.

Do not stop after each milestone. Do not repeatedly ask what to do next if `todos.md` already makes the next step clear.

Make reasonable assumptions and record them in the ledger. Ask for guidance only when truly blocked by:

- missing credentials or access
- destructive or irreversible actions
- ambiguity severe enough that substantial work would likely be wasted

If blocked, update `Blockers`, `Assumptions`, and `Next Actions` before asking.

## Ledger Rules

Follow `references/todo-format.md` for the default layout.

Use root `todos.md` as the canonical top-level ledger. For concurrent work:

- keep shared assumptions and top-level status in root `todos.md`
- keep detailed execution in `todos/<workstream>.md`
- keep the root `Workstreams` section synchronized with per-workstream status

Do not overwrite user-written planning notes carelessly. Preserve unmanaged text where possible and update the managed structured sections in place.

## Reference Map

- `references/planning-workflow.md`: how to do deep collaborative planning before execution
- `references/todo-format.md`: stable markdown layout for root and workstream ledgers
- `references/execution-rules.md`: implementation-mode rules for non-interactive execution
- `references/examples.md`: request shapes that should or should not trigger this skill

## Helper Scripts

- `scripts/init_todos.py`: initialize root `todos.md`, create `todos/`, and optionally create a workstream ledger
- `scripts/update_todos.py`: update structured sections, task states, blockers, assumptions, suggested skills, useful references, and next actions
- `scripts/summarize_todos.py`: emit a concise summary of active workstreams, blockers, and next actions
- `scripts/discover_skills_and_refs.py`: inspect the repo for candidate skills and likely-useful reference files

If the repo already has stronger utilities for these jobs, use them instead of duplicating behavior.

## Hard Rules

- Do not hardcode a fixed list of helper skills into the orchestration method.
- Do not stop after writing a plan unless the task was explicitly planning-only.
- Do not replace a clearly better specialized skill when one is available.
- Do not keep interrupting implementation for confirmation when the ledger already makes the next step clear.
- Do not replace existing user planning notes when an additive update is enough.
