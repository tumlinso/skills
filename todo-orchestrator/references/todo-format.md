# Todo Format

Use a two-level ledger:

- root `todos.md` is the canonical index and shared-status ledger
- `todo-status.md` is the quick pickup register
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
---
slug: "slug"
status: "in_progress"
execution: "claimed"
owner: "unassigned"
created_at: "2026-04-13T13:55:36Z"
last_heartbeat_at: "2026-04-13T13:55:36Z"
last_reviewed_at: "2026-04-13T13:55:36Z"
stale_after_days: 3
objective: "Short purpose"
---

# Current Objective

## Summary

## Quick Start
- Why this stream exists: ...
- In scope: ...
- Out of scope / dependencies: ...
- Required skills: ...
- Required references: ...

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

## `todo-status.md`

```markdown
# Todo Status

## Summary
Use this file as the quick pickup register for `todos.md` workstreams.
- `ready`: planned work that can be started now.
- `claimed`: currently being written; choose another stream.
- `idle`: unfinished but resumable; safe to pick up.
- `closed`: completed or removed from pickup rotation.

## Workstreams
- `slug` | status: planned | execution: ready | owner: unassigned | file: `todos/slug.md` | next: Review the workstream ledger and start the first concrete task.

## Staleness Review
- Fresh: 1
- Aging: 0
- Stale candidates: 0
- Stale: 0
- Superseded: 0

## Cleanup Status
- Cleanup mode is explicit only.
- Safe to call `todo-cleanup`: no, there are unfinished workstreams.
- Partial cleanup may still be available when completed terminal workstreams remain alongside active or stale survivors.
```

## Rules

- treat workstream frontmatter as the authoritative source for lifecycle, freshness, and ownership metadata
- preserve user-written content where possible
- update structured sections in place instead of rewriting the whole file
- keep root `Workstreams` synchronized with per-workstream status
- keep `todo-status.md` synchronized with root status, ownership, and the first actionable next step
- keep `todo-status.md` `Staleness Review` current when `review_staleness.py --apply` runs
- let `Cleanup Status` distinguish between full-cleanup readiness and partial-cleanup availability
- use short, readable bullets instead of opaque machine blobs
- record assumptions instead of blocking when the assumption is safe enough
