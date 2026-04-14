# Status And Cleanup

Use this reference when coordinating parallel workstreams or invoking `todo-cleanup`.

## Pickup Register

Treat `todo-status.md` as the fast scan for fresh threads and delegated agents.

Each entry records:

- the workstream slug
- the canonical workstream status: `planned`, `in_progress`, `blocked`, `stale`, `done`, `superseded`
- the pickup execution state: `ready`, `claimed`, `idle`, `closed`
- the owner label when known
- the workstream file path
- one short next-step summary
- freshness review lives in the `Staleness Review` section rather than in the one-line pickup entry

## Claiming Rules

- `planned` + `ready`: safe to start now; do not leave it waiting if you are the active serial thread
- `in_progress` + `claimed`: currently being written; do not pick it up
- `in_progress` + `idle`: paused but resumable; safe to pick up
- `blocked`: not pickable until the blocker is resolved
- `stale` + `closed`: do not pick it up until it is reviewed or reactivated
- `done` + `closed`: finished; leave it alone unless explicitly cleaning up
- `superseded` + `closed`: terminal and cleanup-eligible

When a thread starts writing a workstream, mark it `claimed`.

When a thread stops before completion, release it back to `idle` and leave a short next step.

When a thread completes the stream, mark it `done` and `closed`.

## Parallel Split Guidance

Only split into workstreams when the boundaries are legible enough that another thread can start from the workstream file alone.

For each workstream, put the high-level pickup context near the top:

- why the stream exists
- what it owns
- what it does not own
- what it depends on
- the exact skills to read before starting
- the exact references to read before starting
- what to do next

If the user does not delegate, continue the streams serially yourself. Do not pause just because a split created multiple streams; if the next stream is unclaimed and `ready` or `idle`, pick it up before asking the user what to do next.

Run `review_staleness.py` before resuming a long-idle stream when there is reason to suspect the ledger drifted from reality.

## Cleanup Rules

`todo-cleanup` is explicit mode.

- Never run it automatically.
- Full cleanup is only safe when every tracked workstream is `done` or `superseded`.
- Partial cleanup is allowed only when the user explicitly requests it.
- Default partial-cleanup scope is completed terminal workstreams.
- `stale` workstreams are not part of the default partial-cleanup scope; include them only when explicitly requested in `--scope`.
- A completed task may notice from `todo-status.md` that cleanup is safe, but it should only report that fact.
- Actual cleanup happens only when the user explicitly asks for `todo-cleanup`.

Cleanup behavior:

- full cleanup deletes every completed or superseded `todos/<workstream>.md` file
- full cleanup removes those entries from `todos.md` and `todo-status.md`
- full cleanup compacts the root/status ledgers to the empty-state form when nothing remains
- partial cleanup deletes only the selected cleanup-eligible `todos/<workstream>.md` files
- partial cleanup removes only those entries from `todos.md` and `todo-status.md`
- partial cleanup rebuilds shared root/status sections from the surviving workstreams rather than preserving stale global context verbatim
