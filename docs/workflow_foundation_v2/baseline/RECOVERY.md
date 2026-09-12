# WF2 donor recovery boundary

The retained donor is recoverable from immutable Git object
`3652874793401944e3cde30a3134aeb5615316ba`; it is not copied into a new
runtime path.  Verify availability with:

```sh
git cat-file -e 3652874793401944e3cde30a3134aeb5615316ba^{commit}
git ls-tree -r --long 3652874793401944e3cde30a3134aeb5615316ba -- todo-orchestrator
```

The accompanying `disposable_fixture_v1.json` is synthetic and versioned. It
is intentionally not a live export, does not name a Cellerator or GlassHelix
database, and contains no active capability/session material. It supports
format-level regression work without modifying a real authority.

Recovery is source-preserving: checkout or inspect the recorded commit in an
isolated worktree only after a separately authorized operational decision.
This baseline neither deploys old code nor creates a replacement authority.
