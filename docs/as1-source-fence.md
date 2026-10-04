# AS1 local publication source fence

When `Service.project_source_verifier` is configured, every amendment or
publication source prerequisite passes through that trusted callback, including
local anchors. Exact known local project UUIDs, project names and configured
project IDs are normalized to the native project UUID before verification.
Repository, path, hash and any pinned UUID/revision remain exact. No repository
alias expansion occurs. Callback refusal, exceptions or incomplete receipts
fail closed; native local filesystem reads cannot rescue a refused source.

Only `project_source_verifier=None` retains the portable native local fallback.
Foreign anchors continue to require a trusted verifier. The callback does not
grant declaration powers: publication still authenticates the claim, task,
publication kind and owned path before checking source prerequisites inside the
native transaction. Failure preserves revision, declarations and event state.

Qualification uses actual imported source with module path and SHA256 checks in
isolated child fixtures and disposable native repositories. Deployment bindings
are removed only from those fixture children, following the existing semantic
port fixture; the live environment and hardware release bindings are unchanged.

```sh
/home/tumlinson/project-control/.venv/bin/python -m pytest \
  todo-orchestrator/tests/test_as1_source_fence.py \
  todo-orchestrator/tests/test_as1_foreign_source_port.py -q
```

The local publication checks exercise host denial, callback exception,
incomplete receipts, UUID/name/configured-ID normalization, unchanged repository
aliases, exact receipt repository/path/hash matching, and no-verifier success
and stale-hash refusal. Denials compare the full native database dump and
revision before and after the transaction. The existing 15 semantic port checks
cover foreign verification and native plan preservation.
