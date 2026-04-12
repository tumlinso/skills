# Todo Format

Use a two-level ledger:

- root `todos.md` is the canonical index and shared-status ledger
- `todos/<workstream>.md` stores the detailed execution plan for each active stream

## Root `todos.md`

```markdown
# Active Objectives

## Summary

## Shared Assumptions

## Suggested Skills

## Useful Reference Files

## Workstreams
- `slug` | status: in_progress | owner: unassigned | file: `todos/slug.md` | objective: Short purpose

## Global Blockers

## Progress Notes

## Next Actions

## Done Criteria
```

## Workstream File

```markdown
# Current Objective

## Summary

## Planning Notes

## Assumptions

## Suggested Skills

## Useful Reference Files

## Plan

## Tasks
- [ ] pending task
- [~] in progress task
- [x] completed task
- [!] blocker

## Blockers

## Progress Notes

## Next Actions

## Done Criteria
```

## Rules

- preserve user-written content where possible
- update structured sections in place instead of rewriting the whole file
- keep root `Workstreams` synchronized with per-workstream status
- use short, readable bullets instead of opaque machine blobs
- record assumptions instead of blocking when the assumption is safe enough
