# Planning Workflow

Use this guide when the task is substantial, ambiguous, or multi-step.

## Goals

- plan extensively with the user before implementation
- turn fuzzy requests into concrete execution steps
- identify assumptions, risks, dependencies, and validation early
- define done criteria before starting implementation
- record the plan in `todos.md` and the active workstream file

## Planning Sequence

1. Ground in the repo before asking questions.
2. Identify the actual objective, constraints, audience, and success criteria.
3. Challenge weak assumptions that would make the plan fragile.
4. Decompose the work into implementation steps that can be executed without further decision-making.
5. Identify likely dependencies, blockers, validation steps, and rollback concerns.
6. Discover relevant repo-local skills and reference files and record them in the ledger.
7. Write the result into `todos.md` and the active workstream file before implementation starts.

## Good Planning Questions

Ask questions that materially change the plan:

- what outcome counts as done
- which behaviors are in or out of scope
- which tradeoff matters most if speed and completeness conflict
- which interfaces, file formats, or user-visible behaviors must remain stable
- which risks would make work expensive to redo later

Avoid asking questions that can be answered from the repo.

## What To Capture

Record these items in the ledger:

- objective summary
- planning notes
- assumptions and defaults
- concrete implementation steps
- validation and test plan
- blockers and external dependencies
- suggested skills
- useful reference files
- next actions
- done criteria

## Transition To Implementation

Planning is complete when:

- the next implementation steps are concrete
- important assumptions are explicit
- likely validation steps are known
- the relevant ledger files are updated

At that point, switch into implementation mode and continue without repeated guidance unless truly blocked.
