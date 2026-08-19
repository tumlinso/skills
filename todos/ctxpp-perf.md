

<!-- todo-orchestrator:v2-managed:start -->
# CTXPP-PERF: Accelerate cpp-context-compiler without API changes

Task revision: `146`; current project revision is in `todo-status.md`.

## Objective
Freeze compatibility, measure the existing implementation, add zero-parse hot queries, lazy local freshness, a private query store, automatic CPU and memory scheduling, targeted semantic refresh, concurrency safety, and measured regression coverage.

## State
- Lifecycle: `done`
- Execution: `closed`
- Parallel policy: `serial`
- Result: `implemented`

## Next Action
Capture compatibility goldens and timing/RSS/work-counter baselines before changing implementation, then implement the cheapest correct query path and adaptive semantic scheduler.

## Ownership
- `exclusive`: `cpp-context-compiler`
- `forbidden`: `todo-status.md`
- `forbidden`: `todos`
- `forbidden`: `todos.md`
- `read`: `AGENTS.md`

## Dependencies
_None._
<!-- todo-orchestrator:v2-managed:end -->
