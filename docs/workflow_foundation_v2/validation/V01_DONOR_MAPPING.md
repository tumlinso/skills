# V01 donor mapping and sensitive-state boundary

This is a reproducible review input, not an acceptance receipt. It maps the
frozen Skills donor at commit `3652874793401944e3cde30a3134aeb5615316ba`.
The source identity is a Git commit and tree objects; it is intentionally not
a claim that a current runtime database has been observed.

## Retained donor release

The complete `todo-orchestrator` subtree remains recoverable from the frozen
commit. Reproduce its root inventory with:

```sh
git ls-tree 3652874793401944e3cde30a3134aeb5615316ba:todo-orchestrator
git ls-tree -r 3652874793401944e3cde30a3134aeb5615316ba -- todo-orchestrator
git cat-file -e 3652874793401944e3cde30a3134aeb5615316ba^{commit}
```

Every root entry has an explicit disposition:

| Donor entry | Disposition |
| --- | --- |
| `SKILL.md` | Retain as the user-facing compatibility entrypoint. |
| `agents` | Retain as instruction/reference material. |
| `pyproject.toml` | Retain as the donor package build identity. |
| `references` | Retain as compatibility and operating references. |
| `schemas` | Retain as persisted-format compatibility material. |
| `scripts` | Retain for explicit operational tooling; do not run implicitly. |
| `tests` | Retain as the donor behavioral baseline. |
| `todo_orchestrator` | Candidate implementation source for qualified, parity-first replacement. |

`workflow_core` is only a future replacement destination after a qualified
parity comparison. This review does not authorize source movement, imports,
or runtime cutover; the frozen donor commit remains the fallback baseline.

## Sensitive state is excluded

The package and this review contain no live `.todo-orchestrator/` state,
SQLite database, state snapshot, capability handle, authority token, or
runtime export. Those are external authorities, never donor package inputs.
The safe review boundary is Git objects at the frozen commit plus this
disposition map. A fresh, separately authorized authority observation is
required for any later import or deployment decision.

## Independent reproduction limits

This map proves the recorded Git donor can be enumerated and recovered. It
does not prove a live release is current, that a runtime database is safe to
copy, or that a replacement has parity. Those claims require external,
hashed evidence and independent review.
