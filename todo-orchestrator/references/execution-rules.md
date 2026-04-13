# Execution Rules

Use these rules after planning is complete.

## Canonical Source Of Truth

- read root `todos.md` before continuing work
- read `todo-status.md` before claiming or resuming a parallel workstream
- read the relevant `todos/<workstream>.md` file for the detailed plan
- treat the ledger as the active execution guide

## Default Behavior

- continue non-interactively when the next action is already clear
- if a stream is `claimed`, choose another stream unless you are the writer releasing or finishing it
- if a stream is `ready` or `idle` and not already claimed elsewhere, pick it up immediately instead of waiting
- update task states, progress notes, assumptions, blockers, and next actions as work proceeds
- keep `todo-status.md` synchronized with pickup state and the short next-step summary
- prefer relevant repo-local skills and reference files when they are a better fit for the current step

## When To Ask

Stop and ask only when:

- credentials or access are missing
- the next step is destructive or irreversible
- ambiguity is severe enough that substantial work would likely be wasted

Before stopping, confirm there is no `ready` or `idle` stream you can advance yourself.

If you stop, write the blocker and the exact missing decision into the ledger first.

## Cleanup

- `todo-cleanup` is explicit mode only
- it may be reported as safe once every tracked workstream is `done`
- it must not run automatically during ordinary execution
