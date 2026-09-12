# WF2 Todo donor baseline

This directory records the **read-only donor baseline** for `todo-orchestrator`
at Skills commit `3652874793401944e3cde30a3134aeb5615316ba`.  It is an inventory,
not an export of any Todo authority: it contains only Git tree metadata,
paths, Git blob object identifiers, byte counts, and static compatibility
observations.  In particular it contains no `.todo-orchestrator` database,
snapshot, task projection, capability handle, session, claim, or runtime
sidecar data.

`todo_orchestrator_inventory.json` is complete for every tracked file below
`todo-orchestrator` at that commit.  Each entry has the Git blob identity and
size; the recorded subtree identity gives an additional whole-tree check.
The acceptance test compares the record with `git ls-tree` for the immutable
baseline commit rather than trusting the current checkout.

## Public-consumer audit

The inventory records exact, versioned references in `cuda`,
`local-coding-worker`, and `cpp-context-compiler`.  These are compatibility
obligations, not permission to change those components.  The audit is bounded
to tracked textual references found by the exact `todo_orchestrator` or
`todo-orchestrator` spellings at the baseline commit.  Dynamic imports,
out-of-tree deployments, generated code, and downstream private repositories
remain unknown external consumers and are therefore a release-blocking
compatibility risk until separately qualified.

The donor's supported packaging identity is also recorded: distribution
`todo-orchestrator`, Python package `todo_orchestrator`, and no console entry
point declared in `todo-orchestrator/pyproject.toml`.  Runtime sidecars are
represented as source paths only; their live contents are intentionally
excluded.
